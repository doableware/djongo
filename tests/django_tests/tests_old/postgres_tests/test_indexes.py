from django.contrib.postgres.indexes import BrinIndex, GinIndex, GistIndex
from django.db import connection
from django.test import skipUnlessDBFeature

from . import PostgreSQLTestCase
from .models import CharFieldModel, DateTimeArrayModel, IntegerArrayModel


@skipUnlessDBFeature('has_brin_index_support')
class BrinIndexTests(PostgreSQLTestCase):

    def test_suffix(self):
        self.assertEqual(BrinIndex.suffix, 'brin')

    def test_not_eq(self):
        index = BrinIndex(fields=['title'])
        index_with_page_range = BrinIndex(fields=['title'], pages_per_range=16)
        self.assertNotEqual(index, index_with_page_range)

    def test_name_auto_generation(self):
        """
        A name longer than 30 characters (since len(BrinIndex.suffix) is 4
        rather than usual limit of 3) is okay for PostgreSQL. For this test,
        the name of the field ('datetimes') must be at least 7 characters to
        generate a name longer than 30 characters.
        """
        index = BrinIndex(fields=['datetimes'])
        index.set_name_with_model(DateTimeArrayModel)
        self.assertEqual(index.name, 'postgres_te_datetim_abf104_brin')

    def test_deconstruction(self):
        index = BrinIndex(fields=['title'], name='test_title_brin')
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, 'django.contrib.postgres.indexes.BrinIndex')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'fields': ['title'], 'name': 'test_title_brin'})

    def test_deconstruction_with_pages_per_range(self):
        index = BrinIndex(fields=['title'], name='test_title_brin', pages_per_range=16)
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, 'django.contrib.postgres.indexes.BrinIndex')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'fields': ['title'], 'name': 'test_title_brin', 'pages_per_range': 16})

    def test_invalid_pages_per_range(self):
        with self.assertRaisesMessage(ValueError, 'pages_per_range must be None or a positive integer'):
            BrinIndex(fields=['title'], name='test_title_brin', pages_per_range=0)


class GinIndexTests(PostgreSQLTestCase):

    def test_suffix(self):
        self.assertEqual(GinIndex.suffix, 'gin')

    def test_eq(self):
        index = GinIndex(fields=['title'])
        same_index = GinIndex(fields=['title'])
        another_index = GinIndex(fields=['author'])
        self.assertEqual(index, same_index)
        self.assertNotEqual(index, another_index)

    def test_name_auto_generation(self):
        index = GinIndex(fields=['field'])
        index.set_name_with_model(IntegerArrayModel)
        self.assertEqual(index.name, 'postgres_te_field_def2f8_gin')

    def test_deconstruction(self):
        index = GinIndex(
            fields=['title'],
            name='test_title_gin',
            fastupdate=True,
            gin_pending_list_limit=128,
        )
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, 'django.contrib.postgres.indexes.GinIndex')
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                'fields': ['title'],
                'name': 'test_title_gin',
                'fastupdate': True,
                'gin_pending_list_limit': 128,
            }
        )

    def test_deconstruct_no_args(self):
        index = GinIndex(fields=['title'], name='test_title_gin')
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, 'django.contrib.postgres.indexes.GinIndex')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'fields': ['title'], 'name': 'test_title_gin'})


class GistIndexTests(PostgreSQLTestCase):

    def test_suffix(self):
        self.assertEqual(GistIndex.suffix, 'gist')

    def test_eq(self):
        index = GistIndex(fields=['title'], fillfactor=64)
        same_index = GistIndex(fields=['title'], fillfactor=64)
        another_index = GistIndex(fields=['author'], buffering=True)
        self.assertEqual(index, same_index)
        self.assertNotEqual(index, another_index)

    def test_name_auto_generation(self):
        index = GistIndex(fields=['field'])
        index.set_name_with_model(CharFieldModel)
        self.assertEqual(index.name, 'postgres_te_field_1e0206_gist')

    def test_deconstruction(self):
        index = GistIndex(fields=['title'], name='test_title_gist', buffering=False, fillfactor=80)
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, 'django.contrib.postgres.indexes.GistIndex')
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                'fields': ['title'],
                'name': 'test_title_gist',
                'buffering': False,
                'fillfactor': 80,
            }
        )

    def test_deconstruction_no_customization(self):
        index = GistIndex(fields=['title'], name='test_title_gist')
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, 'django.contrib.postgres.indexes.GistIndex')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'fields': ['title'], 'name': 'test_title_gist'})


class SchemaTests(PostgreSQLTestCase):

    def get_constraints(self, table):
        """
        Get the indexes on the table using a new cursor.
        """
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def test_gin_index(self):
        # Ensure the table is there and doesn't have an index.
        self.assertNotIn('field', self.get_constraints(IntegerArrayModel._meta.db_table))
        # Add the index
        index_name = 'integer_array_model_field_gin'
        index = GinIndex(fields=['field'], name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(IntegerArrayModel, index)
        constraints = self.get_constraints(IntegerArrayModel._meta.db_table)
        # Check gin index was added
        self.assertEqual(constraints[index_name]['type'], GinIndex.suffix)
        # Drop the index
        with connection.schema_editor() as editor:
            editor.remove_index(IntegerArrayModel, index)
        self.assertNotIn(index_name, self.get_constraints(IntegerArrayModel._meta.db_table))

    def test_gin_fastupdate(self):
        index_name = 'integer_array_gin_fastupdate'
        index = GinIndex(fields=['field'], name=index_name, fastupdate=False)
        with connection.schema_editor() as editor:
            editor.add_index(IntegerArrayModel, index)
        constraints = self.get_constraints(IntegerArrayModel._meta.db_table)
        self.assertEqual(constraints[index_name]['type'], 'gin')
        self.assertEqual(constraints[index_name]['options'], ['fastupdate=off'])
        with connection.schema_editor() as editor:
            editor.remove_index(IntegerArrayModel, index)
        self.assertNotIn(index_name, self.get_constraints(IntegerArrayModel._meta.db_table))

    @skipUnlessDBFeature('has_gin_pending_list_limit')
    def test_gin_parameters(self):
        index_name = 'integer_array_gin_params'
        index = GinIndex(fields=['field'], name=index_name, fastupdate=True, gin_pending_list_limit=64)
        with connection.schema_editor() as editor:
            editor.add_index(IntegerArrayModel, index)
        constraints = self.get_constraints(IntegerArrayModel._meta.db_table)
        self.assertEqual(constraints[index_name]['type'], 'gin')
        self.assertEqual(constraints[index_name]['options'], ['gin_pending_list_limit=64', 'fastupdate=on'])
        with connection.schema_editor() as editor:
            editor.remove_index(IntegerArrayModel, index)
        self.assertNotIn(index_name, self.get_constraints(IntegerArrayModel._meta.db_table))

    @skipUnlessDBFeature('has_brin_index_support')
    def test_brin_index(self):
        index_name = 'char_field_model_field_brin'
        index = BrinIndex(fields=['field'], name=index_name, pages_per_range=4)
        with connection.schema_editor() as editor:
            editor.add_index(CharFieldModel, index)
        constraints = self.get_constraints(CharFieldModel._meta.db_table)
        self.assertEqual(constraints[index_name]['type'], BrinIndex.suffix)
        self.assertEqual(constraints[index_name]['options'], ['pages_per_range=4'])
        with connection.schema_editor() as editor:
            editor.remove_index(CharFieldModel, index)
        self.assertNotIn(index_name, self.get_constraints(CharFieldModel._meta.db_table))

    def test_gist_index(self):
        # Ensure the table is there and doesn't have an index.
        self.assertNotIn('field', self.get_constraints(CharFieldModel._meta.db_table))
        # Add the index.
        index_name = 'char_field_model_field_gist'
        index = GistIndex(fields=['field'], name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(CharFieldModel, index)
        constraints = self.get_constraints(CharFieldModel._meta.db_table)
        # The index was added.
        self.assertEqual(constraints[index_name]['type'], GistIndex.suffix)
        # Drop the index.
        with connection.schema_editor() as editor:
            editor.remove_index(CharFieldModel, index)
        self.assertNotIn(index_name, self.get_constraints(CharFieldModel._meta.db_table))

    def test_gist_parameters(self):
        index_name = 'integer_array_gist_buffering'
        index = GistIndex(fields=['field'], name=index_name, buffering=True, fillfactor=80)
        with connection.schema_editor() as editor:
            editor.add_index(CharFieldModel, index)
        constraints = self.get_constraints(CharFieldModel._meta.db_table)
        self.assertEqual(constraints[index_name]['type'], GistIndex.suffix)
        self.assertEqual(constraints[index_name]['options'], ['buffering=on', 'fillfactor=80'])
        with connection.schema_editor() as editor:
            editor.remove_index(CharFieldModel, index)
        self.assertNotIn(index_name, self.get_constraints(CharFieldModel._meta.db_table))
