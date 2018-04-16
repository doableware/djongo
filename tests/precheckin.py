import sys
import unittest
from djongo_tests.test_sqlparsing import TestParse

if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(
        unittest.TestLoader().loadTestsFromTestCase(TestParse)
    )
    if not result.wasSuccessful():
        sys.exit(1)
