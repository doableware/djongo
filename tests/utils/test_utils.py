import json
import subprocess
import typing
from collections import namedtuple
from functools import cached_property
from itertools import (
    chain
)
import os
from unittest import TestCase

from django.test.runner import DiscoverRunner as DjangoDiscoverRunner
import django, pymongo, djongo
import unittest
from pymongo import MongoClient
from defs import DJONGO_PRIVATE_DIR


QA_REPORT_FILE = f'{DJONGO_PRIVATE_DIR}tests/report.json'
TEST_TAGS_FILE = f'{DJONGO_PRIVATE_DIR}tests/tag_info.json'
TEST_ID_FILE = f'{DJONGO_PRIVATE_DIR}tests/test_id.json'
ReportKey = namedtuple('ReportKey', ('djongo_version',
                                     'django_version',
                                     'pymongo_version',
                                     'commit_id'))


class TestResult(unittest.TestResult):
    success: list[TestCase]
    failures: list[TestCase]
    errors: list[TestCase]

    def __init__(self, *args, **kwargs):
        self.success = []
        super().__init__(*args, **kwargs)

    def addSuccess(self, test):
        self.success.append(test)

    def addFailure(self, test, err):
        self.failures.append(test)

    def addError(self, test, err):
        self.errors.append(test)

class TestRunner(unittest.TextTestRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class DiscoverRunner(DjangoDiscoverRunner):
    test_runner = TestRunner

    def get_resultclass(self):
        return TestResult

    def suite_result(self, suite, result, **kwargs):
        return result

class Value:
    _name: str

    def __set_name__(self, owner, name):
        self._name = name


class ListValue(Value):

    def __init__(self, other: str):
        self._other = other

    def __set_name__(self, owner, name):
        super().__set_name__(owner, name)
        self._value_set_name = f'{self._name}_set'

    def __set__(self, instance: 'Entry', value):
        value_set_name = self._value_set_name
        try:
            value_set = getattr(instance, value_set_name)
        except AttributeError:
            value_set = set()
            setattr(instance, value_set_name, value_set)
        value_set.add(value)

    def __get__(self, instance: 'Entry', owner):
        try:
            current = getattr(instance, self._value_set_name)
        except AttributeError:
            current = set()
        try:
            old = set(instance._entries[self._name])
        except KeyError:
            pass
        else:
            try:
                current = current | (old - getattr(instance, f'{self._other}_set'))
            except AttributeError:
                current = current | old

        return list(current)


# class DictValue(Value):
#
#     def __get__(self, instance: 'Entries', owner: typing.Type['Entries']):
#         try:
#             ret = instance._dict[self._name]
#         except KeyError:
#             ret = owner.valueType({})
#             instance._dict[self._name] = ret
#         except AttributeError:
#             return
#         else:
#             if not isinstance(ret, owner.valueType):
#                 ret = owner.valueType(ret)
#                 instance._dict[self._name] = ret
#
#         # setattr(instance, self._name, ret)
#         return ret
#
#     def __set__(self, instance: 'Entries', value):
#         raise TypeError

class AutoID(Value):
    def __get__(self, instance: 'Entry', owner):
        pass

class LoadFile:
    _file_name: str
    _entries: typing.Union['TestReportEntry', 'TestIdEntry']
    _entries_type: 'entry_types'

    def __init__(self,
                 filename: str = None,
                 entries_type: 'entry_types' = None):
        self._file_name = filename or self._file_name
        self._entries_type = entries_type or self._entries_type

    def __enter__(self):
        try:
            with open(self._file_name, 'r') as fp:
                self._entries = self._entries_type(json.load(fp))
        except FileNotFoundError:
            self._entries = self._entries_type({})
        return self._entries

    def __exit__(self, exc_type, exc_val, exc_tb):
        with open(self._file_name, 'w') as fp:
            json.dump(self._entries, fp, indent=1, default=lambda e: e.to_json())


class Entry:
    _entries: dict
    entries_type: typing.Type['entry_types']

    def __init__(self, _dict):
        self._entries = _dict

    def __getitem__(self, item):
        try:
            entry = self._entries[item]
        except KeyError:
            entry = self.entries_type({})
            self._entries[item] = entry
        else:
            if not isinstance(entry, self.entries_type):
                entry = self.entries_type(entry)
                self._entries[item] = entry
        return entry

    def __setitem__(self, key, value):
        raise TypeError

    def to_json(self):
        return self._entries

class VerdictEntry(Entry):
    passed = ListValue(other='failed')
    failed = ListValue(other='passed')

    def to_json(self):
        return {
            'passed': self.passed,
            'failed': self.failed
        }

class TagEntry(Entry):
    entries_type = VerdictEntry


class TestReportEntry(Entry):
    entries_type = TagEntry


class TestIdEntry(Entry):
    """
    "test1": 1,
    "test2": 2
    """
    def __getitem__(self, item):
        try:
            return  self._entries[item]
        except KeyError:
            try:
                next_id = next(reversed(self._entries.values())) + 1
            except StopIteration:
                next_id = 0
            self._entries[item] = next_id
        return next_id

type entry_types = typing.Union[Entry, VerdictEntry, TagEntry, TestIdEntry]

class TestIdManager(LoadFile):
    test_ids: TestIdEntry | None = None
    _file_name = TEST_ID_FILE
    _entries_type = TestIdEntry

    def __enter__(self):
        TestIdManager.test_ids = super().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.test_ids = super().__exit__(exc_type, exc_val, exc_tb)


class Report:
    report_file: str
    report_entries_type: typing.Type[entry_types]

    def __init__(self, entry: entry_types):
        self.entry = entry

    @classmethod
    def log_test_report(cls, result: TestResult):
        with (LoadFile(cls.report_file, cls.report_entries_type) as report_entries,
              TestIdManager()):
            entry = report_entries[cls.key()]
            report = cls(entry)
            report._log_entry(result)

    @staticmethod
    def key():
        raise NotImplementedError

    def _log_entry(self, result: TestResult):
        raise NotImplementedError

class TestReport(Report):
    report_file = QA_REPORT_FILE
    report_entries_type = TestReportEntry

    def _log_entry(self, result: TestResult):
        entry = self.entry
        test_ids = TestIdManager.test_ids

        result2verdict = {
            'success': 'passed',
            'failures': 'failed',
            'errors': 'failed'
        }
        for result_type, verdict_name in result2verdict.items():
            for test in getattr(result, result_type):
                try:
                    found_tags = getattr(test, 'tags')
                except AttributeError:
                    test_tags = ('missing', 'all')
                else:
                    test_tags = chain(found_tags, ('all',))

                _id = test_ids[test.id()]
                for tag in test_tags:
                    setattr(entry[tag], verdict_name, _id)


    @staticmethod
    def _iter_suite(suite: unittest.TestSuite):
        for item in suite:
            if isinstance(item, unittest.TestCase):
                yield item
            else:
                yield from TestReport._iter_suite(item)

    @staticmethod
    def key():
        o = subprocess.run('git rev-parse --short=11 HEAD',
                           shell=True,
                           check=True,
                           capture_output=True,
                           text=True)
        commit = o.stdout.strip(' \n')
        key = ReportKey(djongo_version=djongo.__version__,
                        django_version=django.__version__,
                        pymongo_version=pymongo.__version__,
                        commit_id=commit)
        key = TestReport._key2str(key)
        return key

    @staticmethod
    def _key2str(key: ReportKey) -> str:
        key_str = ', '.join(key)
        return key_str

    @staticmethod
    def _str2key(string: str) -> ReportKey:
        key_tuple = tuple(string.split(', '))
        key = ReportKey(*key_tuple)
        return key


class _DjangoSetupHelper(unittest.TestCase):
    settings = None

    @classmethod
    def setup(cls):
        cls.setUpClass()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # drop old table
        with MongoClient() as client:
            client.drop_database('djongo-test')
        os.environ["DJANGO_SETTINGS_MODULE"] = cls.settings
        django.setup()


class SetupLiteTestCase(_DjangoSetupHelper):
    settings = "test_project.settings.lite"


class SetupLoadedTestCase(_DjangoSetupHelper):
    settings = "test_project.settings.loaded"