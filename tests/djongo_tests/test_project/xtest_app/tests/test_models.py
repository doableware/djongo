from django.core.exceptions import ValidationError

from djongo.exceptions import NotSupportedError
from xtest_app.models.basic_field import BasicBlog, BasicRelatedEntry, BasicAuthor
from . import TestCase
from djongo import models
from xtest_app.models import basic_field, embedded_field
from typing import Type, Optional as O, Union as U


class FieldTests(TestCase):
    module_path = 'xtest_app.models.basic_field'
    entry_bases = (basic_field.HeadlinedEntry,)
    mongo_field_model_container = basic_field.NamedBlog
    mongo_field = models.EmbeddedField
    blog_value: U[dict, list, None]
    headline_query: dict
    blog_query: dict
    mut: U[Type[models.Model], type]
    entry: embedded_field.EmbeddedFieldEntry
    db_entry: embedded_field.EmbeddedFieldEntry

    def get_model(self,
                  **embedded_field_kwargs) -> U[Type[models.Model], type]:
        field = self.mongo_field(
            model_container=self.mongo_field_model_container,
            **embedded_field_kwargs)
        mut = type('ModelUnderTest',
                   self.entry_bases,
                   {'blog': field,
                    '__module__': self.module_path})
        return mut

    def setUp(self) -> None: # NoQA
        super().setUp()
        self.headline_query = {
            'headline': 'entry_headline',
        }
        self.blog_query = {
            'blog': self.blog_value
        }

    @property
    def entry_values(self):
        return {
            **self.headline_query,
            'blog': self.blog_value
        }


class MongoFieldTests(FieldTests):

    def verify(self):
        self.entry = entry = self.mut.objects.create(**self.entry_values)
        self.db_entry = db_entry = self.mut.objects.get(**self.headline_query)
        self.assertEqual(entry, db_entry)

    def verify_default_options(self):
        self.mut = self.get_model()
        self.verify()

    def verify_fake_extra_value(self, proper_value):
        self.mut = self.get_model()
        with self.assertRaises(AssertionError):
            self.verify()
        self.assertEqual(self.db_entry.blog, proper_value)

    def verify_missing_value(self):
        self.mut = self.get_model()
        entry = self.mut(**self.headline_query)
        with self.assertRaises(ValidationError) as e:
            entry.clean_fields()

    def verify_null_true(self):
        self.mut = self.get_model(null=True, blank=True)
        self.blog_value = None
        entry = self.mut(**self.entry_values)
        entry.clean_fields()

    def verify_null_false(self):
        self.mut = self.get_model(null=False)
        self.blog_value = None
        entry = self.mut(**self.entry_values)
        with self.assertRaises(ValidationError):
            entry.clean_fields()

    def verify_db_column(self):
        self.mut = self.get_model(db_column='other_blog')
        entry = self.mut.objects.create(**self.entry_values)
        count = self.db[self.mut._meta.db_table].count_documents({
            'other_blog': {'$exists': True}})
        self.assertEqual(count, 1)

    def verify_db_default(self, default):
        self.mut = self.get_model(default=default)
        entry = self.mut(**self.headline_query)
        entry.clean_fields()
        entry.save()
        db_entry = self.mut.objects.get(**self.headline_query)
        self.assertEqual(db_entry.blog, default)
        self.assertEqual(entry, db_entry)


class TestEmbeddedField(MongoFieldTests):

    def setUp(self) -> None:
        self.blog_value = {
            'name': 'blog_name'
        }
        super().setUp()

    def test_default_options(self):
        self.verify_default_options()

    def test_fake_extra_value(self):
        proper_value = self.blog_value.copy()
        self.blog_value.update({'fake_name': 'fake_name'})
        self.verify_fake_extra_value(proper_value)

    def test_missing_value(self):
        self.verify_missing_value()

    def test_null_true(self):
        self.verify_null_true()

    def test_null_false(self):
        self.verify_null_false()

    def test_db_column(self):
        self.verify_db_column()

    def test_db_default(self):
        self.verify_db_default(default={'name': 'blog_name'})


class TestEmbeddedInternalField(FieldTests, TestCase):
    named_blog_kwargs: dict
    _entry = None

    @property
    def mongo_field_model_container(self):
        class Meta:
            abstract = True

        kwargs = {
            'Meta': Meta,
            '__module__': self.module_path,
            'name': models.CharField(**self.named_blog_kwargs)
        }
        NamedBlog = type('NamedBlog',
                         (models.Model,),
                         kwargs)
        return NamedBlog

    def setUp(self):
        super().setUp()
        self._entry = None

    @property
    def entry(self):
        if self._entry:
            return self._entry
        self.mut = self.get_model()
        self._entry = self.mut(**self.entry_values)
        return self._entry

    def test_null_false(self):
        self.named_blog_kwargs = {'null': False,
                                  'max_length': 100}
        self.blog_value = {'name': None}
        with self.assertRaises(ValidationError) as e:
            self.entry.clean_fields()

    def test_missing_value(self):
        self.named_blog_kwargs = {'null': False,
                                  'max_length': 100}
        self.blog_value = {}
        with self.assertRaises(ValueError) as e:
            self.entry.clean_fields()

    def test_db_column(self):
        self.named_blog_kwargs = {'db_column': 'diff_blog',
                                  'max_length': 100}
        with self.assertRaises(ValueError) as e:
            entry = self.entry

    def test_db_index(self):
        self.named_blog_kwargs = {'db_index': True,
                                  'max_length': 100}
        with self.assertRaises(NotSupportedError) as e:
            entry = self.entry

class TestNestedEmbeddedField(MongoFieldTests):
    pass


class TestArrayField(MongoFieldTests):
    mongo_field = models.ArrayField

    def setUp(self) -> None:
        self.blog_value = [{'name': 'blog_name1'},
                           {'name': 'blog_name2'}]
        super().setUp()

    def test_default_options(self):
        self.verify_default_options()

    def test_fake_extra_value(self):
        proper_value = [{'name': 'blog_name1'},
                           {'name': 'blog_name2'}]
        self.blog_value[0].update({'fake_name': 'fake_name'})
        self.verify_fake_extra_value(proper_value)

    def test_missing_value(self):
        self.verify_missing_value()

    def test_null_true(self):
        self.verify_null_true()

    def test_null_false(self):
        self.verify_null_false()

    def test_db_column(self):
        self.verify_db_column()

    def test_db_default(self):
        self.verify_db_default(default=[{'name': 'blog_name1'},
                                        {'name': 'blog_name2'}])


class TestArrayInternalField(MongoFieldTests):
    pass


class TestNestedArrayField(MongoFieldTests):
    pass


class TestReference(TestCase):

    def test_create(self):
        e1 = ReferenceEntry.objects.create(
            headline='h1',
        )
        e2 = ReferenceEntry(headline='h2')
        e2.save()

        a1 = ReferenceAuthor.objects.create(
            name='n1',
            email='e1@e1.com'
        )
        a2 = ReferenceAuthor.objects.create(
            name='n2',
            email='e2@e2.com'
        )

        self.assertEqual([], list(e1.authors.all()))
        self.assertEqual([], list(a1.referenceentry_set.all()))

        e1.authors.add(a1)
        self.assertEqual(e1.authors_id, {a1.pk})
        self.assertEqual([a1], list(e1.authors.all()))
        self.assertEqual([e1], list(a1.referenceentry_set.all()))

        e2.authors.add(a1, a2)
        self.assertEqual(e2.authors_id, {a1.pk, a2.pk})
        self.assertEqual([a1, a2], list(e2.authors.all()))
        self.assertEqual([e1, e2], list(a1.referenceentry_set.all()))
        self.assertEqual([e2], list(a2.referenceentry_set.all()))

        g = ReferenceEntry.objects.get(headline='h1')
        self.assertEqual(e1, g)
        g = ReferenceEntry.objects.get(authors__name='n2')
        self.assertEqual(e2, g)
        g = list(ReferenceEntry.objects.filter(authors__name='n1'))
        self.assertEqual([e1, e2], g)

        a2.referenceentry_set.add(e1)
        self.assertEqual(e1.authors_id, {a1.pk, a2.pk})
        self.assertEqual([e1, e2], list(a2.referenceentry_set.all()))

        a2.delete()
        self.assertEqual([a1], list(e2.authors.all()))
        self.assertEqual([a1], list(e1.authors.all()))


class TestBasic(TestCase):

    def test_create(self):
        b1 = BasicBlog.objects.create(
            name='b1',
            tagline='t1'
        )
        b2 = BasicBlog.objects.create(
            name='b2',
            tagline='t2'
        )
        e1 = BasicRelatedEntry.objects.create(
            headline='h1',
            blog=b1
        )
        e2 = BasicRelatedEntry.objects.create(
            headline='h2',
            blog=b2
        )
        a1 = BasicAuthor.objects.create(
            name='a1'
        )
        a2 = BasicAuthor.objects.create(
            name='a2'
        )
        self.assertEqual([], list(e1.authors.all()))
        self.assertEqual([], list(a1.entry_set.all()))

        e1.authors.add(a1)
        self.assertEqual([a1], list(e1.authors.all()))
        self.assertEqual([e1], list(a1.entry_set.all()))

        e2.authors.add(a1, a2)
        self.assertEqual([a1, a2], list(e2.authors.all()))
        self.assertEqual([e1, e2], list(a1.entry_set.all()))
        self.assertEqual([e2], list(a2.entry_set.all()))

        g = BasicRelatedEntry.objects.get(headline='h1')
        self.assertEqual(e1, g)
        g = BasicRelatedEntry.objects.get(authors__name='a2')
        self.assertEqual(e2, g)
        g = list(BasicRelatedEntry.objects.filter(authors__name='a1'))
        self.assertEqual([e1, e2], g)

        a2.entry_set.add(e1)
        self.assertEqual([e1, e2], list(a2.entry_set.all()))

        a2.delete()
        self.assertEqual([a1], list(e2.authors.all()))
        self.assertEqual([a1], list(e1.authors.all()))

    def test_join(self):
        b1 = BasicBlog.objects.create(
            name='b1',
            tagline='t1'
        )
        b2 = BasicBlog.objects.create(
            name='b2',
            tagline='t2'
        )
        e1 = BasicRelatedEntry.objects.create(
            headline='h1',
            blog=b1
        )
        e2 = BasicRelatedEntry.objects.create(
            headline='h2',
            blog=b1
        )
        eqs = BasicRelatedEntry.objects.filter(blog__name='b1').values('id')
        bqs = BasicBlog.objects.filter(id__in=eqs).values('name')
        self.assertEquals(list(bqs), [{'name': 'b1'}, {'name': 'b2'}])


class TestMisc(TestCase):

    def test_create(self):
        e1 = ListEntry()
        e1.authors = ['a1', 'a2']
        e1.headline = 'h1'
        e1.save()
        g = ListEntry.objects.get(
            headline='h1'
        )
        self.assertEqual(e1, g)

        # g = ListEntry.objects.get(
        #     authors={'0.': 'a1'}
        # )
        self.assertEqual(e1, g)
        e2 = DictEntry()
        e2.headline = 'h2'
        e2.blog = {
            'name': 'b1'
        }
        e2.save()
        g = DictEntry.objects.get(
            headline='h2'
        )
        self.assertEqual(e2, g)
        g = DictEntry.objects.get(
            blog={'name': 'b1'}
        )
        self.assertEqual(e2, g)
