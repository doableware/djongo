from typing import Any
from unittest.util import safe_repr

from django.conf import settings
from pymongo import MongoClient
from pymongo.database import Database
from djongo.models import Model
from django.test import TestCase as DjangoTestCase


class TestCase(DjangoTestCase):
    client: MongoClient
    db: Database

    @classmethod
    def setUpClass(cls):
        cls.client = MongoClient()
        db = settings.DATABASES['default']['NAME']
        cls.db = cls.client[db]

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def assertEqual(self,
                    first: Any,
                    second: Any,
                    msg: Any = None) -> None:
        super().assertEqual(first, second, msg)
        if isinstance(first, Model):
            for field in first._meta.get_fields():
                first_field = getattr(first, field.attname)
                second_field = getattr(second, field.attname)
                super().assertEqual(first_field,
                                    second_field)

    def assertNotEqual(self, first: Any,
                       second: Any,
                       msg: Any = None) -> None:
        if isinstance(first, Model):
            for field in first._meta.get_fields():
                first_field = getattr(first, field.attname)
                second_field = getattr(first, field.attname)
                if first_field != second_field:
                    break
            else:
                msg = self._formatMessage(msg, f'{safe_repr(first)} == {safe_repr(second)}')
                raise self.failureException(msg)
        else:
            super().assertNotEqual(first, second, msg)
