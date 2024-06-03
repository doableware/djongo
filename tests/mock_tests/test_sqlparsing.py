import typing
from collections import OrderedDict
from logging import getLogger, DEBUG, StreamHandler
from unittest import TestCase, mock, skip
from unittest.mock import patch, MagicMock, call

from pymongo.command_cursor import CommandCursor
from pymongo.cursor import Cursor

from djongo.base import DatabaseWrapper
from djongo.sql2mongo.query import Query

sqls = [
    'UPDATE "auth_user" '
    'SET "password" = %s, '
    '"last_login" = NULL, '
    '"is_superuser" = %s, '
    '"username" = %s, '
    '"first_name" = %s, '
    '"last_name" = %s, '
    '"email" = %s, '
    '"is_staff" = %s, '
    '"is_active" = %s, '
    '"date_joined" = %s '
    'WHERE "auth_user"."id" = %s',

    'CREATE TABLE "django_migrations" '
    '("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, '
    '"app" char NOT NULL, '
    '"name" char NOT NULL, '
    '"applied" datetime NOT NULL)',

    'SELECT "django_migrations"."app", "django_migrations"."trial" '
    'FROM  "django_migrations" '
    'WHERE ("django_migrations"."app" <=%s '
    'AND "django_migrations"."trial" >=%s '
    'AND "django_migrations"."app" >=%s) '
    'OR ("django_migrations"."app" <=%s '
    'AND "django_migrations"."app">%s)',

    'SELECT "auth_permission"."content_type_id", "auth_permission"."codename" '
    'FROM "auth_permission" INNER JOIN "django_content_type" '
    'ON ("auth_permission"."content_type_id" = "django_content_type"."id") '
    'WHERE "auth_permission"."content_type_id" IN (%(0)s, %(1)s) '
    'ORDER BY "django_content_type"."app_label" ASC,'
    '"django_content_type"."model" ASC, '
    '"auth_permission"."codename" ASC',

    'SELECT "django_content_type"."id", '
    '"django_content_type"."app_label",'
    '"django_content_type"."model" '
    'FROM "django_content_type" '
    'WHERE ("django_content_type"."model" = %s AND "django_content_type"."app_label" = %s)',

    'SELECT (1) AS "a" FROM "django_session" WHERE "django_session"."session_key" = %(0)s LIMIT 1',

    'SELECT COUNT(*) AS "__count" FROM "auth_user"',

    'DELETE FROM "django_session" WHERE "django_session"."session_key" IN (%(0)s)',

    'UPDATE "django_session" SET "session_data" = %(0)s, "expire_date" = %(1)s'
    ' WHERE "django_session"."session_key" = %(2)s',

    'SELECT "django_admin_log"."id", "django_admin_log"."action_time",'
    '"django_admin_log"."user_id", "django_admin_log"."content_type_id",'
    '"django_admin_log"."object_id", "django_admin_log"."object_repr", '
    '"django_admin_log"."action_flag", "django_admin_log"."change_message",'
    '"auth_user"."id", "auth_user"."password", "auth_user"."last_login", '
    '"auth_user"."is_superuser", "auth_user"."username", "auth_user"."first_name",'
    '"auth_user"."last_name", "auth_user"."email", "auth_user"."is_staff",'
    '"auth_user"."is_active", "auth_user"."date_joined", "django_content_type"."id",'
    '"django_content_type"."app_label", "django_content_type"."model" '
    'FROM "django_admin_log" '
    'INNER JOIN "auth_user" '
    'ON ("django_admin_log"."user_id" = "auth_user"."id") '
    'LEFT OUTER JOIN "django_content_type" '
    'ON ("django_admin_log"."content_type_id" = "django_content_type"."id") '
    'WHERE "django_admin_log"."user_id" = %(0)s ORDER BY "django_admin_log"."action_time" DESC LIMIT 10',

    'SELECT "auth_permission"."id", '
    '"auth_permission"."name", '
    '"auth_permission"."content_type_id", '
    '"auth_permission"."codename" '
    'FROM "auth_permission" '
    'INNER JOIN "auth_user_user_permissions" '
    'ON ("auth_permission"."id" = "auth_user_user_permissions"."permission_id") '
    'INNER JOIN "django_content_type" '
    'ON ("auth_permission"."content_type_id" = "django_content_type"."id") '
    'WHERE "auth_user_user_permissions"."user_id" = %s '
    'ORDER BY "django_content_type"."app_label" ASC, '
    '"django_content_type"."model" ASC, '
    '"auth_permission"."codename" ASC',

    'SELECT "auth_permission"."id", "auth_permission"."name", "auth_permission"."content_type_id", '
    '"auth_permission"."codename", "django_content_type"."id", "django_content_type"."app_label", '
    '"django_content_type"."model" '
    'FROM "auth_permission" '
    'INNER JOIN "django_content_type" '
    'ON ("auth_permission"."content_type_id" = "django_content_type"."id") '
    'ORDER BY "django_content_type"."app_label" ASC, "django_content_type"."model" ASC, "auth_permission"."codename" ASC',

    'SELECT "django_admin_log"."id", "django_admin_log"."action_time", '
    '"django_admin_log"."user_id", "django_admin_log"."content_type_id", '
    '"django_admin_log"."object_id", "django_admin_log"."object_repr", '
    '"django_admin_log"."action_flag", "django_admin_log"."change_message", '
    '"auth_user"."id", "auth_user"."password", "auth_user"."last_login", '
    '"auth_user"."is_superuser", "auth_user"."username", "auth_user"."first_name", '
    '"auth_user"."last_name", "auth_user"."email", "auth_user"."is_staff", '
    '"auth_user"."is_active", "auth_user"."date_joined", "django_content_type"."id", '
    '"django_content_type"."app_label", "django_content_type"."model" '
    'FROM "django_admin_log" '
    'INNER JOIN "auth_user" ON ("django_admin_log"."user_id" = "auth_user"."id") '
    'LEFT OUTER JOIN "django_content_type" '
    'ON ("django_admin_log"."content_type_id" = "django_content_type"."id") '
    'WHERE "django_admin_log"."user_id" = %(0)s '
    'ORDER BY "django_admin_log"."action_time" DESC LIMIT 10',

    'SELECT "auth_permission"."id" '
    'FROM "auth_permission" '
    'INNER JOIN "auth_group_permissions" '
    'ON ("auth_permission"."id" = "auth_group_permissions"."permission_id") '
    'INNER JOIN "django_content_type" '
    'ON ("auth_permission"."content_type_id" = "django_content_type"."id") '
    'WHERE "auth_group_permissions"."group_id" = %s '
    'ORDER BY "django_content_type"."app_label" ASC, '
    '"django_content_type"."model" ASC, '
    '"auth_permission"."codename" ASC',

    'SELECT "auth_group_permissions"."permission_id" '
    'FROM "auth_group_permissions" '
    'WHERE ("auth_group_permissions"."group_id" = %s '
    'AND "auth_group_permissions"."permission_id" IN (%s))',

    'SELECT (1) AS "a" '
    'FROM "auth_group" '
    'WHERE ("auth_group"."name" = %(0)s '
    'AND NOT ("auth_group"."id" = %(1)s)) LIMIT 1',

    'SELECT DISTINCT "viewflow_task"."flow_task" '
    'FROM "viewflow_task" '
    'INNER JOIN "viewflow_process" '
    'ON ("viewflow_task"."process_id" = "viewflow_process"."id") '
    'WHERE ("viewflow_process"."flow_class" '
    'IN (%(0)s, %(1)s, %(2)s) '
    'AND "viewflow_task"."owner_id" = %(3)s '
    'AND "viewflow_task"."status" = %(4)s) '
    'ORDER BY "viewflow_task"."flow_task" ASC',

    'SELECT DISTINCT "table1"."col1" '
    'FROM "table1" INNER JOIN "table2" '
    'ON ("table1"."col2" = "table2"."col1") '
    'WHERE ("table2"."flow_class" '
    'IN (%(0)s, %(1)s, %(2)s) '
    'AND "table1"."col3" = %(3)s '
    'AND "table1"."col4" = %(4)s) '
    'ORDER BY "table1"."col1" ASC',

    'SELECT "dummy_multipleblogposts"."id", '
    '"dummy_multipleblogposts"."h1", '
    '"dummy_multipleblogposts"."content" '
    'FROM "dummy_multipleblogposts" '
    'WHERE "dummy_multipleblogposts"."h1" '
    'IN (SELECT U0."id" AS Col1 '
    'FROM "dummy_blogpost" U0 WHERE U0."h1" IN (%s, %s))',

    'SELECT "viewflow_process"."id", '
    '"viewflow_process"."flow_class", '
    '"viewflow_process"."status", '
    '"viewflow_process"."created", '
    '"viewflow_process"."finished" '
    'FROM "viewflow_process" '
    'WHERE "viewflow_process"."id" '
    'IN (SELECT U0."process_id" '
    'AS Col1 FROM "viewflow_task" U0 '
    'INNER JOIN "viewflow_process" U1 '
    'ON (U0."process_id" = U1."id") '
    'WHERE (U1."flow_class" '
    'IN (%(0)s, %(1)s, %(2)s) '
    'AND U0."owner_id" = %(3)s '
    'AND U0."status" = %(4)s)) '
    'ORDER BY "viewflow_process"."created" DESC',

    'SELECT COUNT(*) AS "__count" '
    'FROM "admin_changelist_event" '
    'WHERE "admin_changelist_event"."event_date" '
    'BETWEEN %(0)s AND %(1)s'
]

t1c1 = '"table1"."col1"'
t1c2 = '"table1"."col2"'
t2c1 = '"table2"."col1"'
t2c2 = '"table2"."col2"'
t3c1 = '"table3"."col1"'
t3c2 = '"table3"."col2"'
t4c1 = '"table4"."col1"'
t4c2 = '"table4"."col2"'
t1 = '"table1"'
where = 'SELECT "table1"."col1" FROM "table1" WHERE'

logger = getLogger('djongo')
logger.setLevel(DEBUG)
logger.addHandler(StreamHandler())


class MockTest(TestCase):
    conn = None
    db = None
    sql: str

    @classmethod
    def setUpClass(cls):
        cls.conn = mock.MagicMock()
        cls.db = mock.MagicMock()
        cls.conn_prop = mock.MagicMock()
        cls.conn_prop.cached_collections = ['table', '__schema__']
        cls.params_none = mock.MagicMock()
        cls.params: typing.Union[mock.MagicMock, list] = None

    def setUp(self):
        patcher = patch('djongo.sql2mongo.query.print_warn')
        self.addCleanup(patcher.stop)
        self.print_warn = patcher.start()


class VoidQuery(MockTest):
    base_sql: str

    def exe(self):
        self.result = result = Query(self.conn, self.db, self.conn_prop, self.sql, self.params)
        self.assertRaises(StopIteration, result.next)


class TestCanvasVoidQuery(VoidQuery):

    def test_query(self):
        self.sql = 'ALTER TABLE "table" ADD CONSTRAINT "index" UNIQUE INDEX ("col1") WHERE "col2" IS NULL'
        self.exe()


class TestCreateDatabase(VoidQuery):
    """
    CREATE DATABASE "some_name"
    """

    def test_database(self):
        self.sql = 'CREATE DATABASE "some_name"'
        self.exe()
        self.db.assert_not_called()
        self.conn.assert_not_called()


class TestCreateTable(VoidQuery):
    """
        'CREATE TABLE "django_migrations" '
        '("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, '
        '"app" char NOT NULL, '
        '"name" char NOT NULL, '
        '"applied" datetime NOT NULL)',
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_sql = 'CREATE TABLE "table" '

    def exe(self):
        super().exe()
        self.db.create_collection.assert_called_with('table')

    def test_whitespace(self):
        self.sql = (self.base_sql +
                    '("col 1" int NOT NULL)')
        self.exe()
        calls = [
            call('__schema__'),
            call().update_one(
                filter={'name': 'table'},
                update={'$set': {'fields.col 1': {'type_code': 'int'}}},
                upsert=True
            )
        ]
        self.db.__getitem__.assert_has_calls(calls)
        self.print_warn.assert_called()

    def test_notNull_with_pk(self):
        self.sql = (self.base_sql +
                    '("col1" int NOT NULL PRIMARY KEY, '
                    '"col2" int NOT NULL)')
        self.exe()
        calls = [
            call('table'),
            call().create_index(
                'col1', unique=True, name='__primary_key__'
            ),
            call('__schema__'),
            call().update_one(
                filter={'name': 'table'},
                update={'$set': {'fields.col1': {'type_code': 'int'},
                                 'fields.col2': {'type_code': 'int'}}},
                upsert=True
            )
        ]
        self.db.__getitem__.assert_has_calls(calls)
        self.print_warn.assert_called()

    def test_notNull_with_autoInc(self):
        self.sql = self.base_sql + '("col1" int NOT NULL AUTOINCREMENT)'
        self.exe()
        calls = [
            call('__schema__'),
            call().update_one(
                filter={
                    'name': 'table'
                },
                update={
                    '$set': {
                        'auto.seq': 0,
                        'fields.col1': {'type_code': 'int'}
                    },
                    '$push': {
                        'auto.field_names':
                            {'$each': ['col1']}
                    }
                },
                upsert=True
            ),
        ]
        self.db.__getitem__.assert_has_calls(calls)
        self.print_warn.assert_called()

    def test_notNull_with_unique(self):
        self.sql = self.base_sql + '("col1" int NOT NULL UNIQUE)'
        self.exe()
        calls = [
            call('table'),
            call().create_index(
                 'col1', unique=True
            ),
            call('__schema__'),
            call().update_one(
                filter={'name': 'table'},
                update={'$set': {
                    'fields.col1': {'type_code': 'int'}}},
                upsert=True
            )
        ]
        self.db.__getitem__.assert_has_calls(calls)
        self.print_warn.assert_called()

    def test_pk_with_autoInc(self):
        self.sql = self.base_sql + '("col1" int PRIMARY KEY AUTOINCREMENT)'
        self.exe()
        calls = [
            call('table'),
            call().create_index(
                'col1', unique=True, name='__primary_key__'
            ),
            call('__schema__'),
            call().update_one(
                filter={
                    'name': 'table'
                },
                update={
                    '$set': {
                        'auto.seq': 0,
                        'fields.col1': {'type_code': 'int'}
                    },
                    '$push': {
                        'auto.field_names':
                            {'$each': ['col1']}
                    }
                },
                upsert=True
            )
        ]
        self.db.__getitem__.assert_has_calls(calls)

    def test_pk_with_unique(self):
        self.sql = self.base_sql + '("col1" int PRIMARY KEY UNIQUE)'
        self.exe()
        calls = [
            call('table'),
            call().create_index(
                'col1', unique=True, name='__primary_key__'
            ),
            call('table'),
            call().create_index(
                'col1', unique=True
            ),
            call('__schema__'),
            call().update_one(
                filter={'name': 'table'},
                update={'$set': {
                    'fields.col1': {
                        'type_code': 'int'}}},
                upsert=True
            )
        ]
        self.db.__getitem__.assert_has_calls(calls)

    def test_autoInc_with_unique(self):
        self.sql = self.base_sql + '("col1" int AUTOINCREMENT UNIQUE)'
        self.exe()

        calls = [
            call('table'),
            call().create_index(
                'col1', unique=True
            ),
            call('__schema__'),
            call().update_one(
                filter={
                    'name': 'table'
                },
                update={
                    '$set': {
                        'auto.seq': 0,
                        'fields.col1': {'type_code': 'int'}
                    },
                    '$push': {
                        'auto.field_names':
                            {'$each': ['col1']}
                    }
                },
                upsert=True
            )
        ]
        self.db.__getitem__.assert_has_calls(calls)

    @skip('Test Not ready')
    def test_constraint_notNull(self):
        pass

    @skip('Test Not ready')
    def test_constraint_pk(self):
        pass

    @skip('Test Not ready')
    def test_constraint_autoInc(self):
        pass

    @skip('Test Not ready')
    def test_constraint_unique(self):
        pass



class AlterTable(VoidQuery):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_sql = 'ALTER TABLE "table" '


class TestAlterTable(AlterTable):

    def test_flush(self):
        self.sql = self.base_sql + 'FLUSH'
        self.exe()
        self.db['table'].delete_many.assert_called_with({})


class AlterTableAlterColumn(AlterTable):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_sql += 'ALTER COLUMN "c" '


class TestAlterTableAlterColumn(AlterTableAlterColumn):

    def test_drop_notNull(self):
        self.sql = (self.base_sql +
                    'DROP NOT NULL')
        self.exe()
        self.print_warn.assert_called()
        self.assertFalse(self.db.mock_calls)

    def test_drop_default(self):
        self.sql = (self.base_sql +
                    'DROP DEFAULT')
        self.exe()
        self.print_warn.assert_called()
        self.assertFalse(self.db.mock_calls)

    def test_set_default(self):
        self.sql = (self.base_sql +
                    'SET DEFAULT %s')
        self.exe()
        self.print_warn.assert_called()
        self.assertFalse(self.db.mock_calls)

    def test_set_notNull(self):
        self.sql = (self.base_sql +
                    'SET NOT NULL')
        self.exe()
        self.print_warn.assert_called()
        self.assertFalse(self.db.mock_calls)


class TestAlterTableDrop(AlterTable):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_sql += 'DROP '

    def test_drop_column(self):
        self.sql = (self.base_sql +
                    'COLUMN "c" '
                    'CASCADE')
        self.exe()

        calls = [
            call('table'),
            call().update(
                {},
                {'$unset': {'c': ''}},
                multi=True
            ),
            call('__schema__'),
            call().update(
                {'name': 'table'},
                {'$unset': {'fields.c': ''}}
            )
        ]
        self.db.__getitem__.assert_has_calls(calls)
        self.print_warn.assert_called()

    def test_drop_constraint(self):
        self.sql = (self.base_sql +
                    'CONSTRAINT "c" '
                    'INDEX')
        self.exe()
        calls = [
            call('table'),
            call().drop_index('c')
        ]
        self.db.__getitem__.assert_has_calls(calls)


class TestAlterTableRename(AlterTable):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_sql += 'RENAME '

    def test_rename_column(self):
        self.sql = (self.base_sql +
                    'COLUMN "b" TO "c" ')
        self.exe()
        calls = [
            call('table'),
            call().update(
                {},
                {'$rename': {'b': 'c'}},
                multi=True
            )
        ]
        self.db.__getitem__.assert_has_calls(calls)

    def test_rename_table(self):
        self.sql = (self.base_sql +
                    'TO "table2" ')
        self.exe()
        calls = [
            call('table'),
            call().rename('table2')
        ]
        self.db.__getitem__.assert_has_calls(calls)


class AlterTableAdd(AlterTable):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_sql += 'ADD '


class TestAlterTableAddColumn(AlterTableAdd):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_sql += 'COLUMN "c" '

    def test_default_with_notNull(self):
        self.sql = (self.base_sql +
                    'integer DEFAULT %s NOT NULL ')
        self.params = [2]
        self.exe()
        self.print_warn.assert_called()
        calls = [
            call('table'),

            call().update({'$or': [
                {'c': {'$exists': False}},
                {'c': None}]},
                {'$set': {'c': 2}},
                multi=True),

            call('__schema__'),

            call().update({'name': 'table'},
                          {'$set': {
                              'fields.c': {
                                  'type_code': 'integer'}}})
        ]
        self.db.__getitem__.assert_has_calls(calls)

    def test_notNull_with_unique(self):
        self.sql = (self.base_sql +
                    'integer UNIQUE NOT NULL ')
        self.exe()
        calls = [
            call('table'),
            call().create_index([('c', 1)], name='c', unique=True),
        ]
        self.db.__getitem__.assert_has_calls(calls)
        self.print_warn.assert_called()


class TestAlterTableAddConstraint(AlterTableAdd):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_sql += 'CONSTRAINT "c" '

    def test_fk_refs(self):
        self.sql = (self.base_sql +
                    'FOREIGN KEY ("fk") ' +
                    'REFERENCES "r" ("id")')
        self.exe()
        self.assertFalse(self.db.mock_calls)
        self.print_warn.assert_called()

    def test_index(self):
        self.sql = self.base_sql + 'INDEX ("a", "b")'
        self.exe()
        calls = [
            call('table'),
            call().create_index([('a', 1), ('b', 1)], name='c'),
        ]
        self.db.__getitem__.assert_has_calls(calls)

    def test_unique(self):
        self.sql = self.base_sql + 'UNIQUE ("a", "b")'
        self.exe()
        calls = [
            call('table'),
            call().create_index([('a', 1), ('b', 1)], name='c', unique=True),
        ]
        self.db.__getitem__.assert_has_calls(calls)


class TestDrop(VoidQuery):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_sql = 'DROP '

    def test_drop_db(self):
        self.sql = self.base_sql + 'DATABASE "db"'
        self.exe()
        self.conn.drop_database.assert_called_with('db')

    def test_drop_table(self):
        self.sql = self.base_sql + 'TABLE "table"'
        self.exe()
        self.db.drop_collection.assert_called_with('table')


class TestDelete(VoidQuery):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_sql = 'DELETE FROM "table" '

    def test_where(self):
        self.sql = self.base_sql + 'WHERE "table"."col" < %s'
        self.params = [1]
        self.exe()
        calls = [
            call()('table'),
            call().delete_many(filter={'col': {'$lt': 1}})
        ]
        self.db.__getitem__.assert_has_calls(calls)

    def test_delete_all(self):
        self.sql = self.base_sql
        self.exe()
        calls = [
            call()('table'),
            call().delete_many(filter={})
        ]
        self.db.__getitem__.assert_has_calls(calls)


class TestInsert(VoidQuery):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_sql = 'INSERT INTO "table" '

    def test_single(self):
        self.sql = (self.base_sql +
                    '("col") VALUES (%s)')
        self.params = [1]
        self.exe()
        calls = [
            call()('__schema__'),
            call().find_one_and_update({
                'name': 'table',
                'auto': {'$exists': True}},
                {'$inc': {'auto.seq': 1}},
                return_document=True),

            call()('table'),
            call().insert_many(
                [{'col': 1}],
                ordered=False)
        ]
        self.db.__getitem__.assert_has_calls(calls, any_order=True)

    def test_many(self):
        self.sql = (self.base_sql +
                    '("col") VALUES (%s) VALUES (%s)')
        self.params = [1, 2]
        self.exe()
        calls = [
            call()('__schema__'),
            call().find_one_and_update({
                'name': 'table',
                'auto': {'$exists': True}},
                {'$inc': {'auto.seq': 2}},
                return_document=True),

            call()('table'),
            call().insert_many(
                [{'col': 1}, {'col': 2}],
                ordered=False)
        ]
        self.db.__getitem__.assert_has_calls(calls, any_order=True)

    def test_multi(self):
        self.sql = (self.base_sql +
                    '("col1", "col2") VALUES (%s, %s) VALUES (%s, %s)')
        self.params = [1, 2, 3, 4]
        self.db['table'].insert_many.return_value.inserted_ids = [1, 2]
        self.db['__schema__'].find_one_and_update.return_value = None
        self.exe()
        calls = [
            call()('__schema__'),
            call().find_one_and_update({
                'name': 'table',
                'auto': {'$exists': True}},
                {'$inc': {'auto.seq': 2}},
                return_document=True),

            call()('table'),
            call().insert_many(
                [{'col1': 1, 'col2': 2},
                 {'col1': 3, 'col2': 4}],
                ordered=False)
        ]
        self.db.__getitem__.assert_has_calls(calls, any_order=True)
        self.assertEqual(self.result.last_row_id, 2)

    def test_null(self):
        self.sql = (self.base_sql +
                    '("col1", "col2") VALUES (%s, %s) VALUES (%s, NULL)')
        self.params = [1, 2, 3]
        self.db['table'].insert_many.return_value.inserted_ids = [1, 2]
        self.db['__schema__'].find_one_and_update.return_value = None
        self.exe()
        calls = [
            call()('__schema__'),
            call().find_one_and_update({
                'name': 'table',
                'auto': {'$exists': True}},
                {'$inc': {'auto.seq': 2}},
                return_document=True),

            call()('table'),
            call().insert_many(
                [{'col1': 1, 'col2': 2},
                 {'col1': 3, 'col2': None}],
                ordered=False)
        ]
        self.db.__getitem__.assert_has_calls(calls, any_order=True)
        self.assertEqual(self.result.last_row_id, 2)

    @skip('Insert Default not implemented yet')
    def test_default(self):
        self.sql = (self.base_sql +
                    '("col1", "col2") VALUES (DEFAULT, %s) VALUES (%s, DEFAULT)')
        self.params = [1, 2]
        self.db['table'].insert_many.return_value.inserted_ids = [1, 2]
        self.db['__schema__'].find_one_and_update.return_value = None
        self.exe()
        calls = [
            call()('__schema__'),
            call().find_one_and_update({
                'name': 'table',
                'auto': {'$exists': True}},
                {'$inc': {'auto.seq': 2}},
                return_document=True),

            call()('table'),
            call().insert_many(
                [{'col1': 'DEFAULT', 'col2': 1},
                 {'col1': 2, 'col2': 'DEFAULT'}],
                ordered=False)
        ]
        self.db.__getitem__.assert_has_calls(calls, any_order=True)
        self.assertEqual(self.result.last_row_id, 2)


class TestUpdate(VoidQuery):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_sql = 'UPDATE "table" SET '

    def test_condition(self):
        self.sql = (self.base_sql +
                    '"col1" = %s, "col2" = NULL WHERE "table"."col1" = %s')
        self.params = [1, 2]
        self.exe()
        calls = [
            call()('table'),
            call().update_many(
                filter={'col1': {'$eq': 2}},
                update={'$set': {'col1': 1, 'col2': None}})
        ]
        self.db.__getitem__.assert_has_calls(calls)


@skip
class TestVoidQueryAlter(VoidQuery):
    """
    sql_command: ALTER TABLE "dummy_arrayentry" ADD COLUMN "n_comments" integer DEFAULT %(0)s NOT NULL
    sql_command: ALTER TABLE "dummy_arrayentry" ALTER COLUMN "n_comments" DROP DEFAULT
    """

    def test_pattern1(self):
        self.sql = (
            'ALTER TABLE "table" '
            'FLUSH'
        )
        self.exe()

    def test_pattern2(self):
        self.sql = (
            'ALTER TABLE "table" '
            'ADD CONSTRAINT "con" '
            'FOREIGN KEY ("fk") '
            'REFERENCES "r" ("id")'
        )
        self.exe()

    def test_pattern3(self):
        self.sql = (
            'ALTER TABLE "table" '
            'ADD CONSTRAINT "c"'
            ' UNIQUE ("a", "b")'
        )
        self.exe()

    def test_pattern4(self):
        self.sql = (
            'ALTER TABLE "table" '
            'ALTER COLUMN "c" '
            'DROP NOT NULL'
        )
        self.exe()

    def test_pattern5(self):
        self.sql = (
            'ALTER TABLE "table" '
            'DROP COLUMN "c" '
            'CASCADE'
        )
        self.exe()

    def test_pattern6(self):
        self.sql = (
            'ALTER TABLE "table" '
            'ADD COLUMN "c" '
            'string NOT NULL UNIQUE'
        )
        self.exe()

    def test_pattern7(self):
        self.sql = (
            'ALTER TABLE "table" '
            'ADD COLUMN "c" '
            'integer DEFAULT %s NOT NULL'
        )
        self.params = [1]
        self.exe()


class ResultQuery(MockTest):
    """
    Test the sql2mongo module with all possible SQL statements and check
    if the conversion to a query document is happening properly.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.find = cls.db.__getitem__().find
        cursor = mock.MagicMock()
        cursor.__class__ = Cursor
        cls.iter = cursor.__iter__
        cls.find.return_value = cursor

        cls.aggregate = cls.db.__getitem__().aggregate
        cursor = mock.MagicMock()
        cursor.__class__ = CommandCursor
        cls.agg_iter = cursor.__iter__
        cls.aggregate.return_value = cursor

    def eval_find(self):
        result = Query(self.conn, self.db, self.conn_prop, self.sql, self.params)
        self.db.reset_mock()
        return list(result)

    def eval_aggregate(self, pipeline, iter_return_value=None, ans=None):
        if iter_return_value:
            self.agg_iter.return_value = iter_return_value

        result = list(Query(self.conn, self.db, self.conn_prop, self.sql, self.params))
        self.aggregate.assert_any_call(pipeline)
        if self.params == self.params_none:
            self.params.assert_not_called()
        if ans:
            self.assertEqual(result, ans)

        self.db.reset_mock()


class SelectQuery(ResultQuery):
    part1 = ''
    part2 = ''

    @property
    def sql(self) -> str:
        return f'SELECT {self.part1} {self.part2}'


class TestOrderByAsc(SelectQuery):
    part1 = f'{t1c1}, {t1c2} FROM {t1}'

    def test_desc(self):
        self.part2 = f'ORDER BY {t1c1} ASC, {t1c2} DESC'
        print(self.sql)


class TestQueryDistinct(ResultQuery):

    def test_pattern1(self):
        return_value = [{'col1': 'a'}, {'col1': 'b'}]
        ans = [('a',), ('b',)]

        self.sql = 'SELECT DISTINCT "table1"."col1" FROM "table1" WHERE "table1"."col2" = %s'
        self.params = [1]
        pipeline = [
            {
                '$match': {
                    'col2': {
                        '$eq': 1
                    }
                }
            },
            {
                '$group': {
                    '_id': {'col1': '$col1'}
                }
            },
            {
                '$replaceRoot': {
                    'newRoot': '$_id'
                }
            }
        ]

        self.eval_aggregate(pipeline, return_value, ans)

    def test_pattern2(self):
        return_value = [{'col1': 'a'}, {'col1': 'b'}]
        ans = [('a',), ('b',)]

        self.sql = 'SELECT DISTINCT "table1"."col1" FROM "table1" INNER JOIN "table2" ON ("table1"."id1" = "table2"."id2") WHERE ("table2"."col1" IN (%s, %s, %s)) ORDER BY "table1"."col1" ASC'
        self.params = [1, 2, 3]

        pipeline = [
            {
                '$match': {
                    'id1': {
                        '$ne': None,
                        '$exists': True
                    }
                }
            },
            {
                '$lookup': {
                    'from': 'table2',
                    'localField': 'id1',
                    'foreignField': 'id2',
                    'as': 'table2'
                }
            },
            {
                '$unwind': '$table2'
            },
            {
                '$match': {
                    'table2.col1': {
                        '$in': [1, 2, 3]
                    }
                }
            },
            {
                '$group': {
                    '_id': {'col1': '$col1'}
                }
            },
            {
                '$replaceRoot': {
                    'newRoot': '$_id'
                }
            },
            {
                '$sort': OrderedDict([('col1', 1)])
            },
        ]

        self.eval_aggregate(pipeline, return_value, ans)


class TestQueryFunctions(ResultQuery):

    def test_pattern1(self):
        self.sql = f'SELECT MIN({t1c1}) AS "m__min1", MAX({t1c2}) AS "m__max1"' \
                   f' FROM "table1"'

        pipeline = [
            {'$group': {'_id': None, 'm__min1': {'$min': '$col1'}, 'm__max1': {'$max': '$col2'}}},
            {'$project': {'_id': False, 'm__min1': True, 'm__max1': True}}
        ]
        return_value = [{'m__min1': 1, 'm__max1': 2}]
        ans = [(1, 2)]
        self.eval_aggregate(pipeline, return_value, ans)


class TestQueryCount(ResultQuery):

    def test_count_all(self):
        self.sql = 'SELECT COUNT(*) AS "__count" FROM "table"'
        pipeline = [
            {'$group': {'_id': None, '__count': {'$sum': 1}}},
            {'$project': {'_id': False, '__count': True}}
        ]
        return_value = [{'__count': 1}]
        ans = [(1,)]
        self.eval_aggregate(pipeline, return_value, ans)

    def test_const(self):
        self.sql = 'SELECT (1) AS "a" FROM "table1" WHERE "table1"."col2" = %s LIMIT 1'
        self.params = [2]
        pipeline = [
            {
                '$match': {
                    'col2': {
                        '$eq': 2
                    }
                }
            },
            {
                '$limit': 1
            },
            {
                '$project': {
                    'a': {
                        '$literal': 1
                    }
                }
            },

        ]
        return_value = [{'a': 1}]
        ans = [(1,)]
        self.eval_aggregate(pipeline, return_value, ans)

    def test_const_simple(self):
        self.sql = 'SELECT (1) AS "a" FROM "table1" LIMIT 1'
        self.params = [2]
        pipeline = [
            {
                '$limit': 1
            },
            {
                '$project': {
                    'a': {
                        '$literal': 1
                    }
                }
            },

        ]
        return_value = [{'a': 1}]
        ans = [(1,)]
        self.eval_aggregate(pipeline, return_value, ans)

@skip
class TestQueryUpdate(ResultQuery):

    def test_pattern1(self):
        um = self.conn.__getitem__.return_value.update_many

        sql = 'UPDATE "table" SET "col1" = %s, "col2" = NULL WHERE "table"."col2" = %s'
        params = [1, 2]
        result = Query(self.db, self.conn, self.conn_prop, sql, params)
        um.assert_any_call(filter={'col2': {'$eq': 2}}, update={'$set': {'col1': 1, 'col2': None}})
        self.conn.reset_mock()

    def test_pattern2(self):
        um = self.conn.__getitem__.return_value.update_many
        sql = 'UPDATE "table" SET "col" = %s WHERE "table"."col" = %s'
        params = [1, 2]
        result = Query(self.db, self.conn, self.conn_prop, sql, params)
        um.assert_any_call(filter={'col': {'$eq': 2}}, update={'$set': {'col': 1}})
        self.conn.reset_mock()

    def test_pattern3(self):
        um = self.conn.__getitem__.return_value.update_many
        sql = 'UPDATE "table" SET "col1" = %s WHERE "table"."col2" = %s'
        params = [1, 2]
        result = Query(self.db, self.conn, self.conn_prop, sql, params)
        um.assert_any_call(filter={'col2': {'$eq': 2}}, update={'$set': {'col1': 1}})
        self.conn.reset_mock()

    def test_pattern4(self):
        um = self.conn.__getitem__.return_value.update_many
        sql = 'UPDATE "table" SET "col1" = %s, "col2" = %s WHERE "table"."col2" = %s'
        params = [1, 2, 3]
        result = Query(self.db, self.conn, self.conn_prop, sql, params)
        um.assert_any_call(filter={'col2': {'$eq': 3}}, update={'$set': {'col1': 1, 'col2': 2}})
        self.conn.reset_mock()


class TestQueryInsert(ResultQuery):

    def test_pattern1(self):
        io = self.conn.__getitem__.return_value.insert_many

        sql = 'INSERT INTO "table" ("col1", "col2") VALUES (%s, %s)'
        params = [1, 2]
        result = Query(self.db, self.conn, self.conn_prop, sql, params)
        io.assert_any_call([{'col1': 1, 'col2': 2}], ordered=False)
        self.conn.reset_mock()

    def test_pattern2(self):
        io = self.conn.__getitem__.return_value.insert_many

        sql = 'INSERT INTO "table" ("col1", "col2") VALUES (%s, NULL)'
        params = [1]
        result = Query(self.db, self.conn, self.conn_prop, sql, params)
        io.assert_any_call([{'col1': 1, 'col2': None}], ordered=False)
        self.conn.reset_mock()

    def test_pattern3(self):
        io = self.conn.__getitem__.return_value.insert_many

        sql = 'INSERT INTO "table" ("col") VALUES (%s)'
        params = [1]
        result = Query(self.db, self.conn, self.conn_prop, sql, params)
        io.assert_any_call([{'col': 1}], ordered=False)
        self.conn.reset_mock()

    def test_pattern4(self):
        io = self.conn.__getitem__.return_value.insert_many
        sql = 'INSERT INTO "table" ("col1", "col2") VALUES (%s, %s) VALUES (%s, %s)'
        params = [1, 2, 4, 5]
        result = Query(self.db, self.conn, self.conn_prop, sql, params)
        io.assert_any_call([{'col1': 1, 'col2': 2}, {'col1': 4, 'col2': 5}], ordered=False)
        self.conn.reset_mock()

    def test_pattern5(self):
        """INSERT INTO "m2m_regress_post" ("id") VALUES (DEFAULT)"""

        io = self.conn.__getitem__.return_value.insert_many

        sql = 'INSERT INTO "table" ("id") VALUES (DEFAULT)'
        params = []
        auto = {
            'auto': {
                'field_names': ['id'],
                'seq': 1
            }
        }
        self.conn.__getitem__().find_one_and_update.return_value = auto
        result = Query(self.db, self.conn, self.conn_prop, sql, params)
        io.assert_any_call([{'id': 1}], ordered=False)
        self.conn.reset_mock()


class TestQueryStatement(ResultQuery):

    @skip
    def test_pattern1(self):
        """
        'SELECT * FROM table'
        :return:
        """
        'SELECT "t"."c1" AS Col1, "t"."c2", COUNT("t"."c3") AS "c3__count" FROM "table"'

        self.sql = 'UPDATE "table" SET "col" = %s WHERE "table"."col1" = %s'
        self.params = [1, 2]
        self.eval_find()
        find = self.find


class TestQueryGroupBy(ResultQuery):

    def test_pattern1(self):
        self.sql = (
            f'SELECT {t1c1}, {t1c2}, '
            f'COUNT({t1c1}) AS "c1__count", '
            f'COUNT({t1c2}) AS "c2__count" '
            f'FROM "table1" '
            f'GROUP BY {t1c1}, {t1c2}'
        )
        pipeline = [
            {
                '$group': {
                    '_id': {
                        'col1': '$col1',
                        'col2': '$col2'
                    },
                    'c1__count': {
                        '$sum': {
                            '$cond': {
                                'if': {'$gt': ['$col1', None]},
                                'then': 1,
                                'else': 0}
                        }
                    },
                    'c2__count': {
                        '$sum': {
                            '$cond': {
                                'if': {'$gt': ['$col2', None]},
                                'then': 1,
                                'else': 0}
                        }
                    }
                }
            },
            {
                '$project': {
                    '_id': False,
                    'col1': '$_id.col1',
                    'col2': '$_id.col2',
                    'c1__count': True,
                    'c2__count': True}
            }
        ]
        return_value = [
            {
                'col1': 'a1',
                'col2': 'a2',
                'c1__count': 1,
                'c2__count': 2
            },
            {
                'col1': 'b1',
                'col2': 'b2',
                'c1__count': 3,
                'c2__count': 4
            },
        ]
        ans = [('a1', 'a2', 1, 2), ('b1', 'b2', 3, 4)]
        self.eval_aggregate(pipeline, return_value, ans)

    def test_pattern2(self):
        self.sql = (
            f'SELECT {t1c1}, {t1c2}, MIN({t2c2}) AS "dt" '
            f'FROM "table1" '
            f'LEFT OUTER JOIN "table2" ON ({t1c1} = {t2c2})'
            f' GROUP BY {t1c1}, {t2c2} '
            f'ORDER BY "dt" ASC'
        )

        return_value = [
            {
                'col1': 'a1',
                'col2': 'a2',
                'dt': 1,
            },
            {
                'col1': 'b1',
                'col2': 'b2',
                'dt': 3,
            },
        ]
        ans = [('a1', 'a2', 1), ('b1', 'b2', 3)]
        pipeline = [
            {
                '$lookup': {
                    'from': 'table2',
                    'localField': 'col1',
                    'foreignField': 'col2',
                    'as': 'table2'
                }
            },
            {
                '$unwind': {
                    'path': '$table2',
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$addFields': {
                    'table2': {'$ifNull': ['$table2', {'col2': None}]}
                }
            },
            {
                '$group': {
                    '_id': {
                        'col1': '$col1',
                        'table2': {'col2': '$table2.col2'}},
                    'dt': {'$min': '$table2.col2'}
                }
            },
            {
                '$project': {
                    '_id': False,
                    'col1': '$_id.col1',
                    'col2': '$_id.col2',
                    'dt': True
                }
            },
            {'$sort': OrderedDict([('dt', 1)])}
        ]
        self.eval_aggregate(pipeline, return_value, ans)

    def test_pattern3(self):
        """
        SELECT "timezones_session"."id", "timezones_session"."name", MIN("timezones_sessionevent"."dt") AS "dt" FROM "timezones_session" LEFT OUTER JOIN "timezones_sessionevent" ON ("timezones_session"."id" = "timezones_sessionevent"."session_id") GROUP BY "timezones_session"."id", "timezones_session"."name" HAVING MIN("timezones_sessionevent"."dt") < %(0)s
        """
        self.sql = (
            f'SELECT {t1c1}, {t1c2}, MIN({t2c2}) AS "dt" '
            f'FROM table1 '
            f'LEFT OUTER JOIN "table2" ON ({t1c1} = {t2c2}) '
            f'GROUP BY {t1c1}, {t2c2} '
            f'HAVING MIN({t2c2}) < %s'
        )
        self.params = [2]
        return_value = [
            {
                'col1': 'a1',
                'col2': 'a2',
                'dt': 1,
            },
            {
                'col1': 'b1',
                'col2': 'b2',
                'dt': 0,
            },
        ]
        ans = [('a1', 'a2', 1), ('b1', 'b2', 0)]
        pipeline = [
            {
                '$lookup': {
                    'from': 'table2',
                    'localField': 'col1',
                    'foreignField': 'col2',
                    'as': 'table2'
                }
            },
            {
                '$unwind': {
                    'path': '$table2',
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$addFields': {
                    'table2': {'$ifNull': ['$table2', {'col2': None}]}
                }
            },
            {
                '$group': {
                    '_id': {
                        'col1': '$col1',
                        'table2': {'col2': '$table2.col2'}},
                    'dt': {'$min': '$table2.col2'}
                }
            },
            {
                '$project': {
                    '_id': False,
                    'col1': '$_id.col1',
                    'col2': '$_id.col2',
                    'dt': True
                }
            },
            {
                '$match': {'dt': {'$lt': 2}}
            }
        ]
        self.eval_aggregate(pipeline, return_value, ans)

    @skip
    def test_pattern4(self):
        self.sql = (
            f'SELECT {t1c1}, {t1c2}, COUNT({t2c2}) AS "dt" '
            f'FROM "table1" '
            f'LEFT OUTER JOIN "table2" ON ({t1c1} = {t2c2})'
            f' GROUP BY {t1c1}, {t2c2} '
            f'ORDER BY "dt" ASC'
        )


class TestQuerySpecial(ResultQuery):

    @skip
    def test_pattern1(self):
        """
         SELECT "dummy_multipleblogposts"."id", "dummy_multipleblogposts"."h1", "dummy_multipleblogposts"."content", COUNT("dummy_multipleblogposts"."h1") AS "h1__count", COUNT("dummy_multipleblogposts"."content") AS "content__count" FROM "dummy_multipleblogposts" GROUP BY "dummy_multipleblogposts"."id", "dummy_multipleblogposts"."h1", "dummy_multipleblogposts"."content" LIMIT 21

         :return:
         """
        self.sql = ('SELECT "auth_group"."id", "auth_group"."name" '
                    'FROM "auth_group" '
                    'WHERE (NOT ("auth_group"."name" = %(0)s) '
                    'AND NOT ("auth_group"."name" = %(1)s))')
        find_args = {
            'filter': {
                'col2': {
                    '$eq': 1
                }
            },
            'limit': 1,
            'projection': []
        }
        self.params = ['a', 'b']
        ret = self.eval_find()
        self.assertEqual(ret, [(1,)])
        self.find.assert_any_call(**find_args)
        self.conn.reset_mock()


class TestQueryIn(ResultQuery):

    def test_pattern1(self):
        conn = self.conn
        find = self.find
        iter = self.iter

        # Testing for different combinations 'where' syntax
        # from here on

        where = 'SELECT "table1"."col1", "table1"."col2" FROM "table1" WHERE'
        find_args = {
            'projection': ['col1', 'col2'],
            'filter': {}
        }

        self.sql = f'{where} {t1c1} IN (%s)'
        find_args['filter'] = {
            'col1': {
                '$in': [1]
            }
        }
        self.params = [1]
        iter.return_value = [{'_id': 'x', 'col1': 1, 'col2': 2}, {'_id': 'x', 'col1': 3, 'col2': 4}]
        ans = self.eval_find()
        find.assert_any_call(**find_args)
        self.assertEqual(ans, [(1, 2), (3, 4)])
        conn.reset_mock()

    def test_pattern2(self):
        conn = self.conn
        find = self.find
        iter = self.iter

        # Testing for different combinations 'where' syntax
        # from here on

        where = 'SELECT "table1"."col1", "table1"."col2" FROM "table1" WHERE'
        find_args = {
            'projection': ['col1', 'col2'],
            'filter': {}
        }

        # TODO: This is not the right SQL syntax
        self.sql = f'{where} {t1c1} IN (NULL, %s)'
        find_args['filter'] = {
            'col1': {
                '$in': [None, 1]
            }
        }
        self.params = [1]
        iter.return_value = [{'_id': 'x', 'col1': 1, 'col2': 2}, {'_id': 'x', 'col1': 3, 'col2': 4}]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern3(self):
        conn = self.conn
        find = self.find
        iter = self.iter

        # Testing for different combinations 'where' syntax
        # from here on

        where = 'SELECT "table1"."col1", "table1"."col2" FROM "table1" WHERE'
        find_args = {
            'projection': ['col1', 'col2'],
            'filter': {}
        }

        self.sql = f'{where} {t1c1} IN (NULL)'
        find_args['filter'] = {
            'col1': {
                '$in': [None]
            }
        }
        self.params = []
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern4(self):
        conn = self.conn
        find = self.find
        iter = self.iter

        # Testing for different combinations 'where' syntax
        # from here on

        where = 'SELECT "table1"."col1", "table1"."col2" FROM "table1" WHERE'
        find_args = {
            'projection': ['col1', 'col2'],
            'filter': {}
        }

        self.sql = f'{where} {t1c1} NOT IN (%s)'
        find_args['filter'] = {
            'col1': {
                '$nin': [1]
            }
        }
        self.params = [1]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern5(self):
        conn = self.conn
        find = self.find
        iter = self.iter

        # Testing for different combinations 'where' syntax
        # from here on

        where = 'SELECT "table1"."col1", "table1"."col2" FROM "table1" WHERE'
        find_args = {
            'projection': ['col1', 'col2'],
            'filter': {}
        }

        self.sql = f'{where} {t1c1} NOT IN (%s, %s)'
        find_args['filter'] = {
            'col1': {
                '$nin': [1, 2]
            }
        }
        self.params = [1, 2]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern6(self):
        conn = self.conn
        find = self.find
        iter = self.iter

        # Testing for different combinations 'where' syntax
        # from here on

        where = 'SELECT "table1"."col1", "table1"."col2" FROM "table1" WHERE'
        find_args = {
            'projection': ['col1', 'col2'],
            'filter': {}
        }

        self.sql = f'{where} NOT ({t1c1} IN (%s))'
        find_args['filter'] = {
            'col1': {
                '$nin': [1]
            }
        }
        self.params = [1]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()


class TestQueryJoin(ResultQuery):

    def test_pattern1(self):
        """
         sql_command: SELECT "null_fk_comment"."id", "null_fk_comment"."post_id", "null_fk_comment"."comment_text", "null_fk_post"."id", "null_fk_post"."forum_id", "null_fk_post"."title", "null_fk_forum"."id", "null_fk_forum"."system_info_id", "null_fk_forum"."forum_name", "null_fk_systeminfo"."id", "null_fk_systeminfo"."system_details_id", "null_fk_systeminfo"."system_name" FROM "null_fk_comment" LEFT OUTER JOIN "null_fk_post" ON ("null_fk_comment"."post_id" = "null_fk_post"."id") LEFT OUTER JOIN "null_fk_forum" ON ("null_fk_post"."forum_id" = "null_fk_forum"."id") LEFT OUTER JOIN "null_fk_systeminfo" ON ("null_fk_forum"."system_info_id" = "null_fk_systeminfo"."id") ORDER BY "null_fk_comment"."comment_text" ASC
        :return:
        """
        self.sql = (
            f'SELECT {t1c1}, {t2c1}, {t1c2}, {t2c2} '
            f'FROM table1 '
            f'LEFT OUTER JOIN table2 ON ({t1c1} = {t2c1}) '
            f'LEFT OUTER JOIN table3 ON ({t2c2} = {t3c2}) '
            f'LEFT OUTER JOIN table4 ON ({t3c2} = {t4c1}) '
            f'ORDER BY {t1c1} ASC'
        )
        self.params = []
        return_value = [
            {
                'col1': 'a1',
                'col2': 'a2',
                'table2': {
                    'col1': 'a3',
                    'col2': 'a4'
                }
            },
            {
                'col1': 'b1',
                'col2': 'b2',
                'table2': {
                    'col1': 'b3',
                    'col2': 'b4'
                }
            },
        ]
        ans = [('a1', 'a3', 'a2', 'a4'), ('b1', 'b3', 'b2', 'b4')]
        pipeline = [
            {
                '$lookup': {
                    'from': 'table2',
                    'localField': 'col1',
                    'foreignField': 'col1',
                    'as': 'table2'
                }
            },
            {
                '$unwind': {
                    'path': '$table2',
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$addFields':
                    {'table2': {'$ifNull': ['$table2', {'col1': None, 'col2': None}]}}
            },
            {
                '$lookup': {
                    'from': 'table3',
                    'localField': 'table2.col2',
                    'foreignField': 'col2',
                    'as': 'table3'
                }
            },
            {
                '$unwind': {
                    'path': '$table3',
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$addFields': {'table3': {'$ifNull': ['$table3', {}]}}
            },
            {
                '$lookup': {
                    'from': 'table4',
                    'localField': 'table3.col2',
                    'foreignField': 'col1',
                    'as': 'table4'
                }
            },
            {
                '$unwind': {
                    'path': '$table4',
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$addFields': {'table4': {'$ifNull': ['$table4', {}]}}
            },
            {
                '$sort': OrderedDict([('col1', 1)]),
            },
            {
                '$project': {
                    'col1': True,
                    'col2': True,
                    'table2.col1': True,
                    'table2.col2': True
                }
            }
        ]
        self.eval_aggregate(pipeline, return_value, ans)


class TestQueryNestedIn(ResultQuery):

    def test_pattern1(self):
        return_value = [{'col1': 'a1', 'col2': 'a2'}, {'col1': 'b1', 'col2': 'b2'}]
        ans = [('a1', 'a2'), ('b1', 'b2')]

        self.sql = f'SELECT {t1c1}, {t1c2} ' \
                   f'FROM "table1" ' \
                   f'WHERE ({t1c1} ' \
                   f'IN (SELECT {t2c1} ' \
                   f'FROM "table2" U0 ' \
                   f'WHERE (U0."col2" IN (%s, %s))))'
        self.params = [1, 2]
        inner_pipeline = [
            {
                '$match': {
                    'col2': {
                        '$in': [1, 2]
                    }
                }
            },
            {
                '$project': {
                    'col1': True
                }
            },

        ]
        pipeline = [
            {
                '$lookup': {
                    'from': 'table2',
                    'pipeline': inner_pipeline,
                    'as': '_nested_in'
                }
            },
            {
                '$addFields': {
                    '_nested_in': {
                        '$map': {
                            'input': '$_nested_in',
                            'as': 'lookup_result',
                            'in': '$$lookup_result.col1'
                        }
                    }
                }
            },
            {
                '$match': {
                    '$expr': {
                        '$in': ['$col1', '$_nested_in']
                    }
                }
            },
            {
                '$project': {
                    'col1': True,
                    'col2': True
                }
            },
        ]
        self.eval_aggregate(pipeline, return_value, ans)

    def test_pattern2(self):
        return_value = [{'col1': 'a1', 'col2': 'a2'}, {'col1': 'b1', 'col2': 'b2'}]
        ans = [('a1', 'a2'), ('b1', 'b2')]

        self.sql = f'SELECT {t1c1}, {t1c2} ' \
                   f'FROM "table1" ' \
                   f'WHERE {t1c1} IN (SELECT U0."col1" AS Col1 ' \
                   f'FROM "table2" U0 ' \
                   f'INNER JOIN "table1" U1 ON (U0."col1" = U1."col1") ' \
                   f'WHERE (U1."col2" IN (%s, %s))) ORDER BY {t1c2} DESC'

        self.params = [1, 2, 3, 4, 5]
        inner_pipeline = [
            {
                '$match': {
                    'col1': {
                        '$ne': None,
                        '$exists': True
                    }
                }
            },
            {
                '$lookup': {
                    'from': 'table1',
                    'localField': 'col1',
                    'foreignField': 'col1',
                    'as': 'table1'
                }
            },
            {
                '$unwind': '$table1'
            },
            {
                '$match': {
                    'table1.col2': {
                        '$in': [1, 2]
                    }
                }
            },
            {
                '$project': {
                    'col1': True
                }
            }
        ]
        pipeline = [
            {
                '$lookup': {
                    'from': 'table2',
                    'pipeline': inner_pipeline,
                    'as': '_nested_in'
                }
            },
            {
                '$addFields': {
                    '_nested_in': {
                        '$map': {
                            'input': '$_nested_in',
                            'as': 'lookup_result',
                            'in': '$$lookup_result.col1'
                        }
                    }
                }
            },
            {
                '$match': {
                    '$expr': {
                        '$in': ['$col1', '$_nested_in']
                    }
                }
            },
            {'$sort': OrderedDict([('col2', -1)])},
            {
                '$project': {
                    'col1': True,
                    'col2': True
                }
            },
        ]
        self.eval_aggregate(pipeline, return_value, ans)


class TestQueryNot(ResultQuery):

    def test_pattern1(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} NOT ({t1c1} <= %s)'
        find_args['filter'] = {
            'col1': {
                '$not': {
                    '$lte': 1
                }
            }
        }
        self.params = [1]
        self.iter.return_value = [{'_id': 'x', 'col1': 1}, {'_id': 'x', 'col1': 3, }]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern2(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} NOT {t1c1} <= %s'
        find_args['filter'] = {
            'col1': {
                '$not': {
                    '$lte': 1
                }
            }
        }
        self.params = [1]
        self.iter.return_value = [{'_id': 'x', 'col1': 1}, {'_id': 'x', 'col1': 3, }]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} NOT {t1c1} = NULL'
        find_args['filter'] = {
            'col1': {
                '$not': {
                    '$eq': None
                }
            }
        }
        self.params = []
        self.iter.return_value = [{'_id': 'x', 'col1': 1}, {'_id': 'x', 'col1': 3, }]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern3(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} NOT {t1c1} = NULL'
        find_args['filter'] = {
            'col1': {
                '$not': {
                    '$eq': None
                }
            }
        }
        self.params = []
        self.iter.return_value = [{'_id': 'x', 'col1': 1}, {'_id': 'x', 'col1': 3, }]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()


class TestQueryBasic(ResultQuery):

    def test_pattern1(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} {t1c1} = %s'
        find_args['filter'] = {
            'col1': {
                '$eq': 1
            }
        }
        self.params = [1]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern2(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} {t1c1} <= %s'
        find_args['filter'] = {
            'col1': {
                '$lte': 1
            }
        }
        self.params = [1]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern3(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} {t1c1} = NULL'
        find_args['filter'] = {
            'col1': {
                '$eq': None
            }
        }
        self.params = []
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()


class TestQueryAndOr(ResultQuery):

    def test_pattern1(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} ({t1c1} = %s AND {t1c2} IS NULL)'
        find_args['filter'] = {
            '$and': [
                {
                    'col1': {
                        '$eq': 1
                    }
                },
                {
                    'col2': None
                }
            ]
        }
        self.params = [1, 2]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern2(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} ({t1c1} = %s AND {t1c2} IS NOT NULL)'
        find_args['filter'] = {
            '$and': [
                {
                    'col1': {
                        '$eq': 1
                    }
                },
                {
                    'col2': {'$ne': None}
                }
            ]
        }
        self.params = [1]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern3(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} ({t1c1} = %s AND {t1c1} <= %s)'
        find_args['filter'] = {
            '$and': [
                {
                    'col1': {
                        '$eq': 1
                    }
                },
                {
                    'col1': {
                        '$lte': 2
                    }
                }
            ]
        }
        self.params = [1, 2]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern4(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} (NOT ({t1c1} = %s) AND {t1c1} <= %s)'
        find_args['filter'] = {
            '$and': [
                {
                    'col1': {
                        '$not': {
                            '$eq': 1
                        }
                    }
                },
                {
                    'col1': {
                        '$lte': 2
                    }
                }
            ]
        }
        self.params = [1, 2]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern5(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} {t1c1} <= %s AND NOT ({t1c1} = %s)'
        find_args['filter'] = {
            '$and': [
                {
                    'col1': {
                        '$lte': 2
                    }
                },
                {
                    'col1': {
                        '$not': {
                            '$eq': 1
                        }
                    }
                }
            ]
        }
        self.params = [2, 1]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern6(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} (NOT ({t1c1} <= %s) AND NOT ({t1c1} = %s))'
        find_args['filter'] = {
            '$and': [
                {
                    'col1': {
                        '$not': {
                            '$lte': 2
                        }
                    }
                },
                {
                    'col1': {
                        '$not': {
                            '$eq': 1
                        }
                    }
                }
            ]
        }
        self.params = [2, 1]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern7(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} NOT ({t1c1} <= %s AND {t1c1} = %s)'
        find_args['filter'] = {
            '$or': [
                {
                    'col1': {
                        '$not': {
                            '$lte': 2
                        }
                    }
                },
                {
                    'col1': {
                        '$not': {
                            '$eq': 1
                        }
                    }
                }
            ]
        }
        self.params = [2, 1]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern8(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} NOT ({t1c1} <= %s OR {t1c1} = %s)'
        find_args['filter'] = {
            '$and': [
                {
                    'col1': {
                        '$not': {
                            '$lte': 2
                        }
                    }
                },
                {
                    'col1': {
                        '$not': {
                            '$eq': 1
                        }
                    }
                }
            ]
        }
        self.params = [2, 1]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern9(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} NOT ({t1c1} <= %s OR {t1c1} = %s) AND {t1c1} >= %s'
        find_args['filter'] = {
            '$and': [
                {
                    '$and': [
                        {
                            'col1': {
                                '$not': {
                                    '$lte': 2
                                }
                            }
                        },
                        {
                            'col1': {
                                '$not': {
                                    '$eq': 1
                                }
                            }
                        }
                    ]
                },
                {
                    'col1': {
                        '$gte': 0
                    }
                },
            ]
        }
        self.params = [2, 1, 0]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_pattern10(self):
        conn = self.conn
        find = self.find

        find_args = {
            'projection': ['col1'],
            'filter': {}
        }

        self.sql = f'{where} ({t1c1} BETWEEN %s AND %s)'
        find_args['filter'] = {'col1': {'$gte': 1, '$lte': 2}}
        self.params = [1, 2]
        self.eval_find()
        find.assert_any_call(**find_args)
        conn.reset_mock()


class TestDatabaseWrapper(TestCase):
    """Test cases for connection attempts"""

    def test_empty_connection_params(self):
        """Check for returned connection params if empty settings dict is provided"""
        settings_dict = {}
        wrapper = DatabaseWrapper(settings_dict)
        params = wrapper.get_connection_params()

        self.assertEqual(params['name'], 'djongo_test')
        self.assertEqual(params['enforce_schema'], False)

    def test_connection_params(self):
        """Check for returned connection params if filled settings dict is provided"""
        name = MagicMock()
        port = MagicMock()
        host = MagicMock()

        settings_dict = {
            'NAME': name,
            'CLIENT': {
                'port': port,
                'host': host
            },
        }

        wrapper = DatabaseWrapper(settings_dict)
        params = wrapper.get_connection_params()

        self.assertIs(params['name'], name)
        self.assertIs(params['port'], port)
        self.assertIs(params['host'], host)

    @patch('djongo.database.MongoClient')
    def test_connection(self, mocked_mongoclient):
        settings_dict = MagicMock(dict)
        wrapper = DatabaseWrapper(settings_dict)

        wrapper.get_new_connection(wrapper.get_connection_params())
        mocked_mongoclient.assert_called_once()
