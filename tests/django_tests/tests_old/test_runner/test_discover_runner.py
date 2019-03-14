import os
from argparse import ArgumentParser
from contextlib import contextmanager
from unittest import TestSuite, TextTestRunner, defaultTestLoader

from django.test import TestCase
from django.test.runner import DiscoverRunner
from django.test.utils import captured_stdout


@contextmanager
def change_cwd(directory):
    current_dir = os.path.abspath(os.path.dirname(__file__))
    new_dir = os.path.join(current_dir, directory)
    old_cwd = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(old_cwd)


class DiscoverRunnerTest(TestCase):

    def test_init_debug_mode(self):
        runner = DiscoverRunner()
        self.assertFalse(runner.debug_mode)

    def test_add_arguments_debug_mode(self):
        parser = ArgumentParser()
        DiscoverRunner.add_arguments(parser)

        ns = parser.parse_args([])
        self.assertFalse(ns.debug_mode)
        ns = parser.parse_args(["--debug-mode"])
        self.assertTrue(ns.debug_mode)

    def test_dotted_test_module(self):
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.tests_sample'],
        ).countTestCases()

        self.assertEqual(count, 4)

    def test_dotted_test_class_vanilla_unittest(self):
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.tests_sample.TestVanillaUnittest'],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_dotted_test_class_django_testcase(self):
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.tests_sample.TestDjangoTestCase'],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_dotted_test_method_django_testcase(self):
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.tests_sample.TestDjangoTestCase.test_sample'],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_pattern(self):
        count = DiscoverRunner(
            pattern="*_tests.py",
        ).build_suite(['test_runner_apps.sample']).countTestCases()

        self.assertEqual(count, 1)

    def test_file_path(self):
        with change_cwd(".."):
            count = DiscoverRunner().build_suite(
                ['test_runner_apps/sample/'],
            ).countTestCases()

        self.assertEqual(count, 5)

    def test_empty_label(self):
        """
        If the test label is empty, discovery should happen on the current
        working directory.
        """
        with change_cwd("."):
            suite = DiscoverRunner().build_suite([])
            self.assertEqual(
                suite._tests[0].id().split(".")[0],
                os.path.basename(os.getcwd()),
            )

    def test_empty_test_case(self):
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.tests_sample.EmptyTestCase'],
        ).countTestCases()

        self.assertEqual(count, 0)

    def test_discovery_on_package(self):
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.tests'],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_ignore_adjacent(self):
        """
        When given a dotted path to a module, unittest discovery searches
        not just the module, but also the directory containing the module.

        This results in tests from adjacent modules being run when they
        should not. The discover runner avoids this behavior.
        """
        count = DiscoverRunner().build_suite(
            ['test_runner_apps.sample.empty'],
        ).countTestCases()

        self.assertEqual(count, 0)

    def test_testcase_ordering(self):
        with change_cwd(".."):
            suite = DiscoverRunner().build_suite(['test_runner_apps/sample/'])
            self.assertEqual(
                suite._tests[0].__class__.__name__,
                'TestDjangoTestCase',
                msg="TestDjangoTestCase should be the first test case")
            self.assertEqual(
                suite._tests[1].__class__.__name__,
                'TestZimpleTestCase',
                msg="TestZimpleTestCase should be the second test case")
            # All others can follow in unspecified order, including doctests
            self.assertIn('DocTestCase', [t.__class__.__name__ for t in suite._tests[2:]])

    def test_duplicates_ignored(self):
        """
        Tests shouldn't be discovered twice when discovering on overlapping paths.
        """
        base_app = 'forms_tests'
        sub_app = 'forms_tests.field_tests'
        with self.modify_settings(INSTALLED_APPS={'append': sub_app}):
            single = DiscoverRunner().build_suite([base_app]).countTestCases()
            dups = DiscoverRunner().build_suite([base_app, sub_app]).countTestCases()
        self.assertEqual(single, dups)

    def test_reverse(self):
        """
        Reverse should reorder tests while maintaining the grouping specified
        by ``DiscoverRunner.reorder_by``.
        """
        runner = DiscoverRunner(reverse=True)
        suite = runner.build_suite(
            test_labels=('test_runner_apps.sample', 'test_runner_apps.simple'))
        self.assertIn('test_runner_apps.simple', next(iter(suite)).id(),
                      msg="Test labels should be reversed.")
        suite = runner.build_suite(test_labels=('test_runner_apps.simple',))
        suite = tuple(suite)
        self.assertIn('DjangoCase', suite[0].id(),
                      msg="Test groups should not be reversed.")
        self.assertIn('SimpleCase', suite[4].id(),
                      msg="Test groups order should be preserved.")
        self.assertIn('DjangoCase2', suite[0].id(),
                      msg="Django test cases should be reversed.")
        self.assertIn('SimpleCase2', suite[4].id(),
                      msg="Simple test cases should be reversed.")
        self.assertIn('UnittestCase2', suite[8].id(),
                      msg="Unittest test cases should be reversed.")
        self.assertIn('test_2', suite[0].id(),
                      msg="Methods of Django cases should be reversed.")
        self.assertIn('test_2', suite[4].id(),
                      msg="Methods of simple cases should be reversed.")
        self.assertIn('test_2', suite[8].id(),
                      msg="Methods of unittest cases should be reversed.")

    def test_overridable_get_test_runner_kwargs(self):
        self.assertIsInstance(DiscoverRunner().get_test_runner_kwargs(), dict)

    def test_overridable_test_suite(self):
        self.assertEqual(DiscoverRunner().test_suite, TestSuite)

    def test_overridable_test_runner(self):
        self.assertEqual(DiscoverRunner().test_runner, TextTestRunner)

    def test_overridable_test_loader(self):
        self.assertEqual(DiscoverRunner().test_loader, defaultTestLoader)

    def test_tags(self):
        runner = DiscoverRunner(tags=['core'])
        self.assertEqual(runner.build_suite(['test_runner_apps.tagged.tests']).countTestCases(), 1)
        runner = DiscoverRunner(tags=['fast'])
        self.assertEqual(runner.build_suite(['test_runner_apps.tagged.tests']).countTestCases(), 2)
        runner = DiscoverRunner(tags=['slow'])
        self.assertEqual(runner.build_suite(['test_runner_apps.tagged.tests']).countTestCases(), 2)

    def test_exclude_tags(self):
        runner = DiscoverRunner(tags=['fast'], exclude_tags=['core'])
        self.assertEqual(runner.build_suite(['test_runner_apps.tagged.tests']).countTestCases(), 1)
        runner = DiscoverRunner(tags=['fast'], exclude_tags=['slow'])
        self.assertEqual(runner.build_suite(['test_runner_apps.tagged.tests']).countTestCases(), 0)
        runner = DiscoverRunner(exclude_tags=['slow'])
        self.assertEqual(runner.build_suite(['test_runner_apps.tagged.tests']).countTestCases(), 0)

    def test_tag_inheritance(self):
        def count_tests(**kwargs):
            suite = DiscoverRunner(**kwargs).build_suite(['test_runner_apps.tagged.tests_inheritance'])
            return suite.countTestCases()

        self.assertEqual(count_tests(tags=['foo']), 4)
        self.assertEqual(count_tests(tags=['bar']), 2)
        self.assertEqual(count_tests(tags=['baz']), 2)
        self.assertEqual(count_tests(tags=['foo'], exclude_tags=['bar']), 2)
        self.assertEqual(count_tests(tags=['foo'], exclude_tags=['bar', 'baz']), 1)
        self.assertEqual(count_tests(exclude_tags=['foo']), 0)

    def test_included_tags_displayed(self):
        runner = DiscoverRunner(tags=['foo', 'bar'], verbosity=2)
        with captured_stdout() as stdout:
            runner.build_suite(['test_runner_apps.tagged.tests'])
            self.assertIn('Including test tag(s): bar, foo.\n', stdout.getvalue())

    def test_excluded_tags_displayed(self):
        runner = DiscoverRunner(exclude_tags=['foo', 'bar'], verbosity=3)
        with captured_stdout() as stdout:
            runner.build_suite(['test_runner_apps.tagged.tests'])
            self.assertIn('Excluding test tag(s): bar, foo.\n', stdout.getvalue())
