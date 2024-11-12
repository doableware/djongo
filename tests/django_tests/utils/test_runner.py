import sys
from logging import getLogger, DEBUG, INFO, StreamHandler
from unittest.case import TestCase
from unittest.runner import (
    TextTestResult as BaseTextTestResult,
    TextTestRunner)

from django.test.runner import (
    DiscoverRunner as BaseDiscoverRunner,
    ParallelTestSuite as ParallelSuite,
    RemoteTestRunner as RemoteRunner,
    RemoteTestResult as RemoteResult)


class TextTestResult(BaseTextTestResult):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed = []
        self.handler = StreamHandler(sys.stdout)
        self.stopped = False

    def addSuccess(self, test: TestCase):
        super().addSuccess(test)
        self.stream.writeln('## Ending Test ##')
        self.passed.append((test, ''))
        logger = getLogger('djongo')
        logger.setLevel(INFO)

    def startTest(self, test):
        self.stream.writeln('## Starting Test ##')
        super().startTest(test)
        logger = getLogger('djongo')
        logger.setLevel(INFO)
        if logger.hasHandlers():
            logger.removeHandler(self.handler)
        self.handler = StreamHandler(sys.stdout)
        logger.addHandler(self.handler)

    def stopTest(self, test):
        super().stopTest(test)

    def addError(self, test, err):
        self.errors.append((test, ''))
        self.stream.writeln("ERROR")
        self.stream.writeln('## Ending Test ##')

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.errors.append((test, ''))


class RemoteTestResult(RemoteResult):
    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.events.append(('addSubTest', self.test_index, object(), object()))

    def addError(self, test, err):
        self.events.append(('addError', self.test_index, ''))


class RemoteTestRunner(RemoteRunner):
    resultclass = RemoteTestResult


class ParallelTestSuite(ParallelSuite):
    runner_class = RemoteTestRunner


class TextTestRunnerFactory:

    def __init__(self,
                 buffer=False,
                 result_class=TextTestResult):

        self.buffer = buffer
        self.result_class = result_class

    def __call__(self, *args, **kwargs):
        kwargs['resultclass'] = self.result_class
        return TextTestRunner(buffer=self.buffer,
                              *args,
                              **kwargs)

TestRunner = TextTestRunnerFactory()


class DiscoverRunner(BaseDiscoverRunner):
    test_runner = TestRunner
    parallel_test_suite = ParallelTestSuite

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
