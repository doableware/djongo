import shutil
import subprocess
import sys
import unittest
from mock_tests import test_sqlparsing
import os
from pymongo import MongoClient

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

    client.drop_database('djongo-test')
    manage_py = os.path.join(app_root, "manage.py")
    cmds = [
        'makemigrations dummy',
        'migrate',
        # 'inspectdb',
        # 'test'
    ]
    for cmd in cmds:
        subprocess.run(f'python {manage_py} {cmd}', check=True)