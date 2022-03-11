"""
The citext PostgreSQL extension supports indexing of case-insensitive text
strings and thus eliminates the need for operations such as iexact and other
modifiers to enforce use of an index.
"""
from django.db import IntegrityError
from django.test.utils import modify_settings

from . import PostgreSQLTestCase
from .models import CITestModel


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class CITextTestCase(PostgreSQLTestCase):
    case_sensitive_lookups = ('contains', 'startswith', 'endswith', 'regex')

    @classmethod
    def setUpTestData(cls):
        cls.john = CITestModel.objects.create(
            name='JoHn',
            email='joHn@johN.com',
            description='Average Joe named JoHn',
            array_field=['JoE', 'jOhn'],
        )

    def test_equal_lowercase(self):
        """
        citext removes the need for iexact as the index is case-insensitive.
        """
        self.assertEqual(CITestModel.objects.filter(name=self.john.name.lower()).count(), 1)
        self.assertEqual(CITestModel.objects.filter(email=self.john.email.lower()).count(), 1)
        self.assertEqual(CITestModel.objects.filter(description=self.john.description.lower()).count(), 1)

    def test_fail_citext_primary_key(self):
        """
        Creating an entry for a citext field used as a primary key which
        clashes with an existing value isn't allowed.
        """
        with self.assertRaises(IntegrityError):
            CITestModel.objects.create(name='John')

    def test_array_field(self):
        instance = CITestModel.objects.get()
        self.assertEqual(instance.array_field, self.john.array_field)
        self.assertTrue(CITestModel.objects.filter(array_field__contains=['joe']).exists())

    def test_lookups_name_char(self):
        for lookup in self.case_sensitive_lookups:
            with self.subTest(lookup=lookup):
                query = {'name__{}'.format(lookup): 'john'}
                self.assertSequenceEqual(CITestModel.objects.filter(**query), [self.john])

    def test_lookups_description_text(self):
        for lookup, string in zip(self.case_sensitive_lookups, ('average', 'average joe', 'john', 'Joe.named')):
            with self.subTest(lookup=lookup, string=string):
                query = {'description__{}'.format(lookup): string}
                self.assertSequenceEqual(CITestModel.objects.filter(**query), [self.john])

    def test_lookups_email(self):
        for lookup, string in zip(self.case_sensitive_lookups, ('john', 'john', 'john.com', 'john.com')):
            with self.subTest(lookup=lookup, string=string):
                query = {'email__{}'.format(lookup): string}
                self.assertSequenceEqual(CITestModel.objects.filter(**query), [self.john])
