"""
test_setup.py needs to be separate from test_models so that models.py from aut
is not imported in this case.
"""
import os
import pathlib
import subprocess
from unittest import (
    TestCase,
    main
)
from django.core.management import call_command
from test_utils import (
    SetupLiteTestCase,
    SetupLoadedTestCase
)


class _SetupApps(TestCase):

    def test_setup(self):
        call_command('makemigrations')
        call_command('migrate')


class TestSingleAppSetup(SetupLiteTestCase, _SetupApps):
    pass


class TestAllAppSetup(SetupLoadedTestCase, _SetupApps):
    pass


class TestSetupApps(TestCase):
    tags = ['basic']

    @classmethod
    def setUpClass(cls):
        cls.file = file = pathlib.Path(__file__)
        # test_project = file.parent.parent.parent
        # utils = test_project.parent.joinpath('utils')
        # os.environ["PYTHON_PATH"] = ':'.join(filter(None, (test_project.as_posix(),
        #                                              utils.as_posix(),
        #                                              os.environ.get("PYTHON_PATH"))))

    @staticmethod
    def _run(cmd: str):
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

    def test_single_app_setup(self):
        """
        Basic sanity test, Checks for:
        * New MongoClient connection
        * Introspect DB and list all existing tables
        * Create table: django_migrations, etc.,
        * Read table: django_migrations, etc.,
        """
        self.tags.append('django_boot')
        # Needs to be run as a separate process due to
        # Django setup which is per process.
        self._run(f'python3 {__file__} TestSingleAppSetup')

    def test_all_app_setup(self):
        """
        Sets up the most common django apps
        """
        self._run(f'python3 {__file__} TestAllAppSetup')


if __name__ == '__main__':
    main()

