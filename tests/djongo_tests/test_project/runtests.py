from itertools import chain
from unittest import (
    TestCase,
    defaultTestLoader,
    main
)

from test_utils import (
    DiscoverRunner,
    SetupLiteTestCase,
    TestReport,
    TestRunner,
)

from aut.tests.test_setup import TestSetupApps

class RunTests(TestCase):

    def setUp(self):
        self.normal_suite = defaultTestLoader.loadTestsFromTestCase(TestSetupApps)
        SetupLiteTestCase.setup()
        from aut.tests import test_models
        self.django_suite = defaultTestLoader.loadTestsFromModule(test_models)

    def test_runtests(self):
        runner = TestRunner()
        result = runner.run(self.normal_suite)
        TestReport.log_test_report(result)

        runner = DiscoverRunner()
        result = runner.run_suite(self.django_suite)
        TestReport.log_test_report(result)

    def test_log_tag_info(self):
        TestReport.log_test_tags(chain(self.django_suite, self.normal_suite))

if __name__ == '__main__':
    main()