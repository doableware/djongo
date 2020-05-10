import sys
from logging import getLogger, DEBUG, INFO, StreamHandler
from unittest.case import TestCase
from unittest.runner import (
    TextTestResult as BaseTextTestResult,
    TextTestRunner)

from django.test.runner import DiscoverRunner as BaseDiscoverRunner


class TextTestResult(BaseTextTestResult):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed = []
        self.handler = StreamHandler(sys.stdout)

    def addSuccess(self, test: TestCase):
        super().addSuccess(test)
        self.passed.append(test)
        self.stream.write('\n## Ending Test ##')
        logger = getLogger('djongo')
        logger.setLevel(INFO)

    def startTest(self, test):
        self.stream.write('## Starting Test ##\n')
        super().startTest(test)
        logger = getLogger('djongo')
        logger.setLevel(DEBUG)
        if logger.hasHandlers():
            logger.removeHandler(self.handler)
        self.handler = StreamHandler(sys.stdout)
        logger.addHandler(self.handler)


class TextTestRunnerFactory:

    def __init__(self, buffer=True):
        self.buffer = buffer

    def __call__(self, *args, **kwargs):
        kwargs['resultclass'] = TextTestResult
        return TextTestRunner(buffer=self.buffer,
                              *args,
                              **kwargs)


TestRunner = TextTestRunnerFactory()


class DiscoverRunner(BaseDiscoverRunner):
    test_runner = TestRunner

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        self.setup_test_environment()
        suite = self.build_suite(test_labels, extra_tests)
        databases = self.get_databases(suite)
        old_config = self.setup_databases(aliases=databases)
        run_failed = False
        result = None
        try:
            self.run_checks()
            result = self.run_suite(suite)
        except Exception:
            run_failed = True
            raise
        finally:
            try:
                self.teardown_databases(old_config)
                self.teardown_test_environment()
            except Exception:
                # Silence teardown exceptions if an exception was raised during
                # runs to avoid shadowing it.
                if not run_failed:
                    raise
        return result
