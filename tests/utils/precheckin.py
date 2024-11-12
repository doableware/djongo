#!/usr/bin/env python
import os
import shutil
import subprocess
import sys
import unittest

from pymongo import MongoClient
from mock_tests import test_sqlparsing

client = MongoClient()
TEST_DIR = os.path.dirname(os.path.realpath(__file__))


def remove_migrations(path):
    if 'migrations' in os.listdir(path):
        shutil.rmtree(os.path.join(path, 'migrations'))


def run_test_sqlparsing():
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(
        unittest.defaultTestLoader.loadTestsFromModule(test_sqlparsing)
    )
    if not result.wasSuccessful():
        sys.exit(1)


def run_commands(path):
    with client:
        client.drop_database('djongo-test')

    manage_py = os.path.join(path, "manage.py")
    cmds = [
        'makemigrations xtest_app',
        'migrate',
        'inspectdb',
    ]

    settings = '--settings=test_project.settings.settings_loaded'
    for cmd in cmds:
        print(f'python {manage_py} {cmd} {settings}')
        subprocess.run(f'python {manage_py} {cmd} {settings}'.split(), check=True)

    settings = '--settings=test_project.settings.settings_lite'
    cmd = 'test xtest_app.tests.test_models'
    print(f'python {manage_py} {cmd} {settings}')
    subprocess.run(f'python {manage_py} {cmd} {settings}'.split(), check=True)


if __name__ == '__main__':
    run_test_sqlparsing()
    app_root = os.path.join(TEST_DIR, '../djongo_tests', 'test_project')
    main_test_app = os.path.join(app_root, 'xtest_app')
    remove_migrations(main_test_app)
    run_commands(app_root)
    print('Precheckin DONE')
    remove_migrations(main_test_app)
