import argparse
import json
import os
import shutil
import importlib.util
import subprocess
import sys
from json import JSONDecodeError

MANAGE_DIR = os.path.dirname(os.path.realpath(__file__))
DJANGO_TESTS_ROOT = os.path.dirname(MANAGE_DIR)

TEST_DIR = os.path.join(
    DJANGO_TESTS_ROOT,
    'tests',
    'v21',
    'tests')

django_version = None
db_type = None

PARSER_ARGS = {
    '--start-index': {
        'default': None,
        'type': int,
        'dest': 'start_index'
    },
    '--django-version': {
        'default': '21',
        'type': str,
        'dest': 'django_version'
    },
    '--db-type': {
        'default': 'mongodb',
        'type': str,
        'dest': 'db_type'
    },
    '--run-currently-passing': {
        'action': 'store_true',
        'dest': 'run_currently_passing'
    },
    '--discover-passing': {
        'action': 'store_true',
        'dest': 'discover_passing'
    },
    '--discover-tests': {
        'action': 'store_true',
        'dest': 'discover_tests'
    },
    '--run-specific': {
        'default': None,
        'type': str,
        'dest': 'run_specific'
    },
}

DEFAULT_TESTRUNNER_ARGS = {
    'failfast': '--failfast',
    # 'parallel': '--parallel=1'
}

SETTINGS_FILE = {
    'mongodb': '--settings=test_mongodb',
    'sqlite': '--settings=test_sqlite',
}


def check_settings():
    settings_folder = os.path.join(MANAGE_DIR, 'settings', 'test_mongodb.py')
    test_folder = os.path.join(TEST_DIR, 'test_mongodb.py')
    shutil.copyfile(settings_folder, test_folder)

    settings_folder = os.path.join(MANAGE_DIR, 'settings', 'test_sqlite.py')
    test_folder = os.path.join(TEST_DIR, 'test_sqlite.py')
    shutil.copyfile(settings_folder, test_folder)


def get_django_parser():
    spec = importlib.util.spec_from_file_location('runtests', os.path.join(TEST_DIR, 'runtests.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.parser


def extract_useful_args(args: list):
    ret = []
    for arg in args:
        for parser_arg in PARSER_ARGS.keys():
            if arg.startswith(parser_arg):
                break
        else:
            ret.append(arg)
    return ret


def build_args(args: list, parsed_args):
    uargs = extract_useful_args(args)

    for option in DEFAULT_TESTRUNNER_ARGS:
        if (not hasattr(parsed_args, option)
                or getattr(parsed_args, option) is None):
            uargs.append(DEFAULT_TESTRUNNER_ARGS[option])

    uargs.append(SETTINGS_FILE[db_type])
    path = os.path.join(TEST_DIR, 'runtests.py')
    return [path, 'test_name'] + uargs


def get_file_contents():
    try:
        with open(os.path.join(MANAGE_DIR, 'tests_list.json'), 'r') as fp:
            file_contents = json.load(fp)

    except FileNotFoundError:
        with open(os.path.join(MANAGE_DIR, 'tests_list.json'), 'x') as _:
            pass
        file_contents = {}

    except JSONDecodeError:
        file_contents = {}

    return file_contents


def get_tests_list():
    file_contents = get_file_contents()

    try:
        test_list = file_contents[django_version][db_type]
    except KeyError:
        test_list = {
            'all_tests': [],
            'failing_tests': []
        }
    return test_list


def dump_test_list(test_list):
    file_contents = get_file_contents()
    file_contents[django_version][db_type] = test_list

    with open(os.path.join(MANAGE_DIR, 'tests_list.json'), 'w') as fp:
        json.dump(file_contents, fp)


def discover_tests():
    dirs = os.listdir(TEST_DIR)
    for i, adir in enumerate(dirs[:]):
        if (adir.endswith('.py')
                or adir.endswith('coveragerc')
                or adir.endswith('__')
                or adir.endswith('.rst')
        ):
            dirs.pop(i)

    tests = get_tests_list()
    tests['all_tests'] = dirs
    dump_test_list(tests)


def discover_passing(_parsed):
    tests = get_tests_list()
    orig_args = sys.argv
    sys.argv = build_args(orig_args[1:], _parsed)
    currently_failing = []

    for i, atest in enumerate(tests['all_tests']):
        sys.argv[1] = atest
        print(f'## Executing test: {atest} no: {i}/{len(tests["all_tests"])} ##\n', flush=True)
        o = subprocess.run((['python'] + sys.argv))
        if o.returncode != 0:
            currently_failing.append(atest)

    sys.argv = orig_args
    currently_failing.sort()
    tests['failing_tests'] = currently_failing
    dump_test_list(tests)


def check_passing(_parsed):
    tests = get_tests_list()
    passing = set(tests['all_tests']) - set(tests['failing_tests'])

    pass_exit_code = 0
    fail_exit_code = 1
    orig_args = sys.argv
    sys.argv = build_args(orig_args[1:], _parsed)

    for i, atest in enumerate(passing):
        sys.argv[1] = atest
        print(f'## Executing test: {atest} no: {i}/{len(passing)} ##\n', flush=True)
        o = subprocess.run((['python'] + sys.argv))
        if o.returncode != 0:
            sys.argv = orig_args
            return fail_exit_code
        print(f'## Ran test: {atest}##\n', flush=True)

    sys.argv = orig_args
    return pass_exit_code


def check_specific(_parsed, atest):
    pass_exit_code = 0
    fail_exit_code = 1
    orig_args = sys.argv
    sys.argv = build_args(orig_args[1:], _parsed)

    sys.argv[1] = atest
    print(f'## Executing test: {atest}##\n', flush=True)
    o = subprocess.run((['python'] + sys.argv))
    if o.returncode != 0:
        sys.argv = orig_args
        return fail_exit_code
    print(f'## Ran test: {atest}##\n', flush=True)

    sys.argv = orig_args
    return pass_exit_code

def get_parser():
    _parser = argparse.ArgumentParser(parents=[get_django_parser()], add_help=False)
    for option, arg in PARSER_ARGS.items():
        _parser.add_argument(option, **arg)

    return _parser


if __name__ == '__main__':
    parser = get_parser()
    parsed = parser.parse_args()
    django_version = 'v' + parsed.django_version
    db_type = parsed.db_type

    TEST_DIR = os.path.join(
        DJANGO_TESTS_ROOT,
        'tests',
        django_version,
        'tests')
    check_settings()

    if parsed.discover_tests:
        discover_tests()
    if parsed.discover_passing:
        discover_passing(parsed)
    if parsed.run_currently_passing:
        exit(check_passing(parsed))
    if parsed.run_specific:
        exit(check_specific(parsed, parsed.run_specific))
