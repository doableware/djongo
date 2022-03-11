#!/usr/bin/env python
import argparse
import json
import os
import sys
from itertools import chain
# from typing import Literal

from test_utils import setup_tests

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
UTILS_DIR = os.path.join(ROOT_DIR, 'test_utils',)
TEST_REPO_DIR = os.path.join(
    ROOT_DIR,
    'tests'
)
TEST_RESULTS_FILE = os.path.join(ROOT_DIR, 'results', 'test_list.json')

TEST_VERSIONS = ('v21', 'v22', 'v30')
PY_VERSIONS = ('p36', 'p38')
DB_VERSIONS = ('sqlite', 'mongodb')

# TEST_LITERAL = Literal['v21', 'v22', 'v30']
# PY_LITERAL = Literal['p36', 'p38']
# DB_LITERAL = Literal['sqlite', 'mongodb']

#
# class TestResult(TypedDict):
#     passing: List[str]
#     failing: List[str]
#
# class TestName(TypedDict):
#     migrations: TestResult
#
# class DbVersions(TypedDict):
#     sqlite: TestName
#     mongodb: TestName
#
#
# class PyVersions(TypedDict):
#     p36: DbVersions
#     p38: DbVersions
#     repo_tests: List[str]
#
#
# class TestVersions(TypedDict):
#     v21: PyVersions
#     v22: PyVersions
#     v30: PyVersions


PARSER_ARGS = {
    '--start-index': {
        'default': None,
        'type': int,
        'dest': 'start_index'
    },
    '--django-version': {
        'default': 32,
        'type': int,
        'choices': [21, 22, 30, 32]
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
