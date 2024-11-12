#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import unittest
from importlib import import_module
from itertools import chain
from pathlib import Path
import django

from test_utils import (
    Entry,
    Report,
    TestIdManager,
    TestResult,
    VerdictEntry
)
# from typing import Literal

# from utils import setup_tests

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
UTILS_DIR = os.path.join(ROOT_DIR, 'utils', )
TEST_REPO_DIR = os.path.join(
    ROOT_DIR,
    'tests'
)
TEST_RESULTS_FILE = os.path.join(ROOT_DIR, 'results', 'test_list.json')

TEST_VERSIONS = ('v21', 'v22', 'v30')
PY_VERSIONS = ('p36', 'p38')
DB_VERSIONS = ('sqlite', 'mongodb')


PARSER_ARGS = {
    '--start-index': {
        'default': None,
        'type': int,
        'dest': 'start_index'
    },
    '--django-version': {
        'default': 21,
        'type': int,
        'choices': [21, 22, 30]
    },
    '--db-type': {
        'default': 'mongodb',
        'type': str,
        'choices': ['mongodb', 'sqlite']
    },
    '--check-currently-passing': {
        'action': 'store_true',
    },
    '--discover-passing': {
        'action': 'store_true',
    },
    '--discover-tests': {
        'action': 'store_true',
    },
    '--check-specific': {
        'action': 'store_true',
    },
}

check_tests = [
    'bulk_create',
    'migrations',
    'inspectdb',
    'indexes',
    'dbshell',
    'db_utils',
    'db_typecasts',
    'db_functions',
    'datetimes',
    'dates',
    'datatypes',
    'aggregation']


class DjangoReportEntries(Entry):
    entries_type = VerdictEntry

class DjangoReport(Report):
    report_file = Path(__file__).parent / 'django_report.json'
    report_entries_type = DjangoReportEntries

    @staticmethod
    def key():
        return django.__version__

    def _log_entry(self, result: TestResult):
        entry = self.entry
        test_ids = TestIdManager.test_ids
        for test in result.success:
            entry.passed = test_ids[test.id()]
        for test in chain(result.failures, result.errors):
            entry.failed = test_ids[test.id()]


class RunTests(unittest.TestCase):
    version = '3.1.11'
    test_dir = Path(__file__).parent / 'tests' / version

    kwargs = {
        'verbosity': 1,
        'interactive': False,
        'failfast': True,
        'keepdb': True,
        'reverse': False,
        'test_labels': check_tests,
        'debug_sql': False,
        'parallel': 1,
        'tags': None,
        'exclude_tags': None,
        'test_name_patterns': None,
        'start_at': None,
        'start_after': None,
        'pdb': False,
        'buffer': False,
    }

    @staticmethod
    def _run(cmd: str):
        print(f'Running: {cmd}')
        try:
            o = subprocess.run(cmd,
                               shell=True,
                               check=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               text=True)
        except subprocess.CalledProcessError as e:
            print(e.stdout)
            raise
        print(o.stdout)

    def test_runtest(self):
        sys.path.insert(0, str(self.test_dir.absolute()))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_sqlite')
        settings = import_module('test_sqlite')
        settings.TEST_RUNNER = 'test_utils.DiscoverRunner'
        runtests = import_module('django_tests')
        result = runtests.django_tests(**self.kwargs)
        if result:
            DjangoReport.log_test_report(result)

    def test_clone_django(self):
        version = self.version
        test_dir = self.test_dir
        clone_dir = test_dir / '.clone'
        self._run(f'git clone --branch {version} '
                  f'https://github.com/django/django '
                  f'{clone_dir.absolute()}')
        clone_tests_dir = clone_dir / 'tests'
        self._run(f'mv {clone_tests_dir.absolute()}/* {test_dir}')
        self._run(f'rm -rf {clone_dir.absolute()}')
        run_tests = test_dir / 'runtests.py'
        run_tests.replace(run_tests.with_stem('django_tests'))

class TestManager:

    def __init__(self):
        parser = argparse.ArgumentParser(parents=[setup_tests.get_parser()], add_help=False)
        for option, arg in PARSER_ARGS.items():
            parser.add_argument(option, **arg)
        parsed = self.parsed = parser.parse_args()
        setup_tests.validate_parsed(parsed, parser)

        django_version = f'v{parsed.django_version}'
        python_version = f'p{sys.version_info.major}{sys.version_info.minor}'
        self.selected_test_dir = os.path.join(
            TEST_REPO_DIR,
            django_version,
            'tests'
        )

        sys.path.insert(0, UTILS_DIR)
        sys.path.insert(0, self.selected_test_dir)
        if parsed.db_type == 'mongodb':
            os.environ['DJANGO_SETTINGS_MODULE'] = 'settings.test_mongodb'
        else:
            os.environ['DJANGO_SETTINGS_MODULE'] = 'settings.test_sqlite'
        setup_tests.RUNTESTS_DIR = self.selected_test_dir

        self.test_list = self.load_test_list()
        self.repo_tests_list = self.test_list[django_version]['repo_tests']
        self.result_list = self.test_list[django_version][python_version][parsed.db_type]

    def check_passing(self):
        passing = self.result_list['passing']
        tests = []
        for test in passing.values():
            tests.extend(test)

        self.parsed.modules = tests
        return self.check_specific()

    def discover_tests(self):
        testlist = setup_tests.get_test_list(self.parsed)
        testlist.sort()
        self.repo_tests_list.extend(testlist)

    @staticmethod
    def to_result_dict(test_result):
        res_dict = {}
        for test, trace in test_result:
            _id = test.id()
            name, _ = _id.split('.', 1)
            try:
                res_dict[name].append(_id)
            except KeyError:
                res_dict[name] = [_id]
        for ids in res_dict.values():
            ids.sort()
        return res_dict

    def discover_passing(self):
        if not self.repo_tests_list:
            self.discover_tests()
        self.parsed.modules = self.parsed.modules or check_tests
        result = setup_tests.test_exec(self.parsed)
        res_dict = self.to_result_dict(chain(result.failures,
                                             result.errors,
                                             result.unexpectedSuccesses))
        self.result_list['failing'].update(res_dict)
        res_dict = self.to_result_dict(result.passed)
        self.result_list['passing'].update(res_dict)

    def check_specific(self):
        result = setup_tests.test_exec(self.parsed)
        if any(chain(result.failures, result.errors, result.unexpectedSuccesses)):
            return -1
        else:
            return 0

    def run(self):
        if self.parsed.discover_tests:
            self.discover_tests()
            self.store_test_list(self.test_list)

        if self.parsed.discover_passing:
            self.discover_passing()
            self.store_test_list(self.test_list)

        if self.parsed.check_currently_passing:
            return self.check_passing()

        if self.parsed.check_specific:
            return self.check_specific()

    @staticmethod
    def store_test_list(test_data):
        with open(TEST_RESULTS_FILE, 'w') as fp:
            json.dump(test_data, fp, indent=3)

    @staticmethod
    def load_test_list():
        try:
            with open(TEST_RESULTS_FILE, 'r') as fp:
                return json.load(fp)
        except FileNotFoundError:
            test_list = {}
            for tv in TEST_VERSIONS:
                test_list[tv] = {}
                test_list[tv]['repo_tests'] = []
                for pv in PY_VERSIONS:
                    test_list[tv][pv] = {}
                    for dbv in DB_VERSIONS:
                        test_list[tv][pv][dbv] = {}
                        test_list[tv][pv][dbv]['passing'] = {}
                        test_list[tv][pv][dbv]['failing'] = {}
            return test_list


if __name__ == '__main__':
    tm = TestManager()
    exit(tm.run())
