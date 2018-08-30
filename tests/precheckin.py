import os
import shutil
import subprocess
import sys
import unittest

from pymongo import MongoClient

from mock_tests import test_sqlparsing

client = MongoClient()
TEST_DIR = os.path.dirname(os.path.abspath(__file__))

if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(
        unittest.TestLoader().loadTestsFromModule(test_sqlparsing)
    )
    if not result.wasSuccessful():
        sys.exit(1)

    app_root = os.path.join(TEST_DIR, 'djongo_tests', 'project')
    dummy_app = os.path.join(app_root, 'dummy')
    if 'migrations' in os.listdir(dummy_app):
        shutil.rmtree(os.path.join(dummy_app, 'migrations'))
        print('Migrations removed')

    with client:
        client.drop_database('djongo-test')

    manage_py = os.path.join(app_root, "manage.py")
    cmds = [
        'makemigrations dummy',
        'migrate',
        'inspectdb',
        'test dummy.tests.test_models'
    ]
    settings = '--settings=project.settings_precheckin'
    for cmd in cmds:
        print(f'python {manage_py} {cmd} {settings}')
        subprocess.run(f'python {manage_py} {cmd} {settings}', check=True)