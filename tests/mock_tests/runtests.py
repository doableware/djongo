from unittest import (
    TestCase,
    defaultTestLoader,
    main)

from test_utils import (
    TestReport,
    TestRunner,
)
import test_sqlparsing


class RunTests(TestCase):
    def setUp(self):
        self.suite = defaultTestLoader.loadTestsFromModule(test_sqlparsing)

    def test_runtests(self):
        runner = TestRunner()
        result = runner.run(self.suite)
        TestReport.log_test_report(result)

if __name__ == '__main__':
    main()