#!/usr/bin/env python
import argparse
import json
import os
import shutil
import importlib.util
import subprocess
import sys
from itertools import chain
from json import JSONDecodeError
from typing import Literal

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

TEST_LITERAL = Literal['v21', 'v22', 'v30']
PY_LITERAL = Literal['p36', 'p38']
DB_LITERAL = Literal['sqlite', 'mongodb']

#
# class TestResult(TypedDict):
#     passing: List[str]
#     failing: List[str]
#
#
# class DbVersions(TypedDict):
#     sqlite: TestResult
#     mongodb: TestResult
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
        'default': 21,
        'type': int,
        'choices': [21, 22, 30]
    },
    '--python-version': {
        'default': 38,
        'type': int,
        'choices': [36, 38]
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
    '--run-specific': {
        'default': None,
        'type': str,
    },
}

# DEFAULT_TESTRUNNER_ARGS = {
#     'failfast': '--failfast',
#     # 'parallel': '--parallel=1'
# }
#
# SETTINGS_FILE = {
#     'mongodb': '--settings=test_mongodb',
#     'sqlite': '--settings=test_sqlite',
# }


# def check_settings():
#     settings_folder = os.path.join(MANAGE_DIR, 'test_utils/manage_tests/test_utils/settings', 'test_mongodb.py')
#     test_folder = os.path.join(TEST_REPO_DIR, 'test_mongodb.py')
#     shutil.copyfile(settings_folder, test_folder)
#
#     settings_folder = os.path.join(MANAGE_DIR, 'test_utils/manage_tests/test_utils/settings', 'test_sqlite.py')
#     test_folder = os.path.join(TEST_REPO_DIR, 'test_sqlite.py')
#     shutil.copyfile(settings_folder, test_folder)

#
# def get_django_parser():
#     spec = importlib.util.spec_from_file_location('runtests', os.path.join(TEST_REPO_DIR, 'setup_tests.py'))
#     module = importlib.util.module_from_spec(spec)
#     spec.loader.exec_module(module)
#     return module.parser
#
#
# def extract_useful_args(args: list):
#     ret = []
#     for arg in args:
#         for parser_arg in PARSER_ARGS.keys():
#             if arg.startswith(parser_arg):
#                 break
#         else:
#             ret.append(arg)
#     return ret
#
#
# def build_args(args: list, parsed_args):
#     uargs = extract_useful_args(args)
#
#     for option in DEFAULT_TESTRUNNER_ARGS:
#         if (not hasattr(parsed_args, option)
#                 or getattr(parsed_args, option) is None):
#             uargs.append(DEFAULT_TESTRUNNER_ARGS[option])
#
#     uargs.append(SETTINGS_FILE[db_type])
#     path = os.path.join(TEST_REPO_DIR, 'setup_tests.py')
#     return [path, 'test_name'] + uargs
#
#
# def get_file_contents():
#     try:
#         with open(os.path.join(MANAGE_DIR, 'manage_tests/tests_list.json'), 'r') as fp:
#             file_contents = json.load(fp)
#
#     except FileNotFoundError:
#         with open(os.path.join(MANAGE_DIR, 'manage_tests/tests_list.json'), 'x') as _:
#             pass
#         file_contents = {}
#
#     except JSONDecodeError:
#         file_contents = {}
#
#     return file_contents
#
#
# def get_tests_list():
#     file_contents = get_file_contents()
#
#     try:
#         test_list = file_contents[django_version][db_type]
#     except KeyError:
#         test_list = {
#             'all_tests': [],
#             'failing_tests': []
#         }
#     return test_list
#
#
# def dump_test_list(test_list):
#     file_contents = get_file_contents()
#     file_contents[django_version][db_type] = test_list
#
#     with open(os.path.join(MANAGE_DIR, 'manage_tests/tests_list.json'), 'w') as fp:
#         json.dump(file_contents, fp)
#
#
# def discover_tests():
#     dirs = os.listdir(TEST_REPO_DIR)
#     for i, adir in enumerate(dirs[:]):
#         if (adir.endswith('.py')
#                 or adir.endswith('coveragerc')
#                 or adir.endswith('__')
#                 or adir.endswith('.rst')
#         ):
#             dirs.pop(i)
#
#     tests = get_tests_list()
#     tests['all_tests'] = dirs
#     dump_test_list(tests)
#
#
# def discover_passing(_parsed):
#     tests = get_tests_list()
#     orig_args = sys.argv
#     sys.argv = build_args(orig_args[1:], _parsed)
#     currently_failing = []
#
#     for i, atest in enumerate(tests['all_tests']):
#         sys.argv[1] = atest
#         print(f'## Executing test: {atest} no: {i}/{len(tests["all_tests"])} ##\n', flush=True)
#         o = subprocess.run((['python'] + sys.argv))
#         if o.returncode != 0:
#             currently_failing.append(atest)
#
#     sys.argv = orig_args
#     currently_failing.sort()
#     tests['failing_tests'] = currently_failing
#     dump_test_list(tests)
#
#
# def check_passing(_parsed):
#     tests = get_tests_list()
#     passing = set(tests['all_tests']) - set(tests['failing_tests'])
#
#     pass_exit_code = 0
#     fail_exit_code = 1
#     orig_args = sys.argv
#     sys.argv = build_args(orig_args[1:], _parsed)
#
#     for i, atest in enumerate(passing):
#         sys.argv[1] = atest
#         print(f'## Executing test: {atest} no: {i}/{len(passing)} ##\n', flush=True)
#         o = subprocess.run((['python'] + sys.argv))
#         if o.returncode != 0:
#             sys.argv = orig_args
#             return fail_exit_code
#         print(f'## Ran test: {atest}##\n', flush=True)
#
#     sys.argv = orig_args
#     return pass_exit_code
#
#
# def check_specific(_parsed, atest):
#     pass_exit_code = 0
#     fail_exit_code = 1
#     orig_args = sys.argv
#     sys.argv = build_args(orig_args[1:], _parsed)
#
#     sys.argv[1] = atest
#     print(f'## Executing test: {atest}##\n', flush=True)
#     o = subprocess.run((['python'] + sys.argv))
#     if o.returncode != 0:
#         sys.argv = orig_args
#         return fail_exit_code
#     print(f'## Ran test: {atest}##\n', flush=True)
#
#     sys.argv = orig_args
#     return pass_exit_code

# def get_parser():
#     _parser = argparse.ArgumentParser(parents=[get_django_parser()], add_help=False)
#     for option, arg in PARSER_ARGS.items():
#         _parser.add_argument(option, **arg)
#
#     return _parser


class TestManager:

    def __init__(self):
        parser = argparse.ArgumentParser(parents=[setup_tests.get_parser()], add_help=False)
        for option, arg in PARSER_ARGS.items():
            parser.add_argument(option, **arg)
        parsed = self.parsed = parser.parse_args()
        setup_tests.validate_parsed(parsed, parser)

        django_version = f'v{parsed.django_version}'
        python_version = f'p{parsed.python_version}'
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
        pass

    def discover_tests(self):
        testlist = setup_tests.get_test_list(self.parsed)
        testlist.sort()
        self.repo_tests_list.extend(testlist)

    def discover_passing(self):
        if not self.repo_tests_list:
            self.discover_tests()
        # self.parsed.modules = ['admin_changelist.tests.ChangeListTests']
        result = setup_tests.test_exec(self.parsed)

        self.result_list['failing'].clear()
        for test, trace in chain(result.failures, result.errors, result.unexpectedSuccesses):
            self.result_list['failing'].append(test.id())
        self.result_list['failing'].sort()

        self.result_list['passing'].clear()
        for test in result.passed:
            self.result_list['passing'].append(test.id())
        self.result_list['passing'].sort()

    def run(self):
        if self.parsed.discover_tests:
            self.discover_tests()
            self.store_test_list(self.test_list)

        if self.parsed.discover_passing:
            self.discover_passing()
            self.store_test_list(self.test_list)

        if self.parsed.check_currently_passing:
            return check_passing()
        if self.parsed.run_specific:
            return check_specific()

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
                        test_list[tv][pv][dbv]['passing'] = []
                        test_list[tv][pv][dbv]['failing'] = []
            return test_list



if __name__ == '__main__':
    tm = TestManager()
    exit(tm.run())

    # parser = get_parser()
    # parsed = parser.parse_args()
    # django_version = 'v' + parsed.django_version
    # db_type = parsed.db_type
    #
    # TEST_REPO_DIR = os.path.join(
    #     ROOT_DIR,
    #     'django_tests/tests',
    #     django_version,
    #     'tests')
    # check_settings()
    #
    # if parsed.discover_tests:
    #     discover_tests()
    # if parsed.discover_passing:
    #     discover_passing(parsed)
    # if parsed.run_currently_passing:
    #     exit(check_passing(parsed))
    # if parsed.run_specific:
    #     exit(check_specific(parsed, parsed.run_specific))
