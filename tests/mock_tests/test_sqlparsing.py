import typing
from collections import OrderedDict
from logging import getLogger, DEBUG, StreamHandler
from unittest import TestCase, mock, skip
from unittest.mock import patch, MagicMock

from pymongo.command_cursor import CommandCursor
from pymongo.cursor import Cursor

from djongo.base import DatabaseWrapper
from djongo.sql2mongo.query import Result

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

root_logger = getLogger()
root_logger.setLevel(DEBUG)
root_logger.addHandler(StreamHandler())


class MockTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.conn = mock.MagicMock()
        cls.db = mock.MagicMock()
        cls.conn_prop = mock.MagicMock()
        cls.conn_prop.cached_collections = ['table']
        cls.params_none = mock.MagicMock()
        cls.params: typing.Union[mock.MagicMock, list] = None


class TestVoidQuery(MockTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def exe(self):
        result = Result(self.db, self.conn, self.conn_prop, self.sql, self.params)

    @skip
    def test_delete(self):
        self.sql = 'DELETE FROM "table" WHERE "table"."col" IN (%s)'

    def test_alter(self):
        self.sql = (
            'ALTER TABLE "table" '
            'FLUSH'
        )
        self.exe()

        self.sql = (
            'ALTER TABLE "table" '
            'ADD CONSTRAINT "con" '
            'FOREIGN KEY ("fk") '
            'REFERENCES "r" ("id")'
        )
        self.exe()

        self.sql = (
            'ALTER TABLE "table" '
            'ADD CONSTRAINT "c"'
            ' UNIQUE ("a", "b")'
        )
        self.exe()

        self.sql = (
            'ALTER TABLE "table" '
            'ALTER COLUMN "c" '
            'DROP NOT NULL'
        )
        self.exe()

        self.sql = (
            'ALTER TABLE "table" '
            'DROP COLUMN "c" '
            'CASCADE'
        )
        self.exe()

        self.sql = (
            'ALTER TABLE "table" '
            'ADD COLUMN "c" '
            'integer DEFAULT %s NOT NULL'
        )
        self.params = [1]
        self.exe()
        """
        sql_command: ALTER TABLE "dummy_arrayentry" ADD COLUMN "n_comments" integer DEFAULT %(0)s NOT NULL
        sql_command: ALTER TABLE "dummy_arrayentry" ALTER COLUMN "n_comments" DROP DEFAULT
        """


class TestQuery(MockTest):
    """
    Test the sql2mongo module with all possible SQL statements and check
    if the conversion to a query document is happening properly.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.find = cls.conn.__getitem__().find
        cursor = mock.MagicMock()
        cursor.__class__ = Cursor
        cls.iter = cursor.__iter__
        cls.find.return_value = cursor

        cls.aggregate = cls.conn.__getitem__().aggregate
        cursor = mock.MagicMock()
        cursor.__class__ = CommandCursor
        cls.agg_iter = cursor.__iter__
        cls.aggregate.return_value = cursor


    def find_mock(self):
        result = Result(self.db, self.conn, self.conn_prop, self.sql, self.params)
        return list(result)

    def aggregate_mock(self, pipeline, iter_return_value=None, ans=None):
        if iter_return_value:
            self.agg_iter.return_value = iter_return_value

        result = list(Result(self.db, self.conn, self.conn_prop, self.sql, self.params))
        self.aggregate.assert_any_call(pipeline)
        if self.params == self.params_none:
            self.params.assert_not_called()
        if ans:
            self.assertEqual(result, ans)

        self.conn.reset_mock()

    def test_distinct(self):
        return_value = [{'col1': 'a'}, {'col1': 'b'}]
        ans = [('a',),('b',)]

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

        self.aggregate_mock(pipeline, return_value, ans)

        self.sql = 'SELECT DISTINCT "table1"."col1" FROM "table1" INNER JOIN "table2" ON ("table1"."id1" = "table2"."id2") WHERE ("table2"."col1" IN (%s, %s, %s)) ORDER BY "table1"."col1" ASC'
        self.params = [1,2,3]

        pipeline =[
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
                        '$in': [1,2,3]
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

        self.aggregate_mock(pipeline, return_value, ans)

    def test_functions(self):
        t1c1 = '"table1"."col1"'
        t2c1 = '"table2"."col1"'
        t4c1 = '"table4"."col1"'

        t1c2 = '"table1"."col2"'
        t2c2 = '"table2"."col2"'
        t3c2 = '"table3"."col2"'
        t3c1 = '"table3"."col1"'

        self.sql = f'SELECT MIN({t1c1}) AS "m__min1", MAX({t1c2}) AS "m__max1"' \
                   f' FROM "table1"'

        pipeline = [{'$group': {'_id': None, 'm__min1': {'$min': '$col1'}, 'm__max1': {'$max': '$col2'}}}]
        return_value = [{'m__min1': 1, 'm__max1': 2}]
        ans = [(1,2)]
        self.aggregate_mock(pipeline, return_value, ans)

    def test_count(self):
        conn = self.conn
        agg = self.aggregate
        iter = self.iter

        self.sql = 'SELECT COUNT(*) AS "__count" FROM "table"'
        pipeline = [{
            '$count': '_count'
        }]
        return_value = [{'_count': 1}]
        ans = [(1,)]
        self.aggregate_mock(pipeline, return_value, ans)

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
                    '_const': {
                        '$literal': 1
                    }
                }
            },

        ]
        return_value = [{'_const': 1}]
        ans = [(1,)]
        self.aggregate_mock(pipeline, return_value, ans)

        self.sql = 'SELECT (1) AS "a" FROM "table1" LIMIT 1'
        self.params = [2]
        pipeline = [
            {
                '$limit': 1
            },
            {
                '$project': {
                    '_const': {
                        '$literal': 1
                    }
                }
            },

        ]
        return_value = [{'_const': 1}]
        ans = [(1,)]
        self.aggregate_mock(pipeline, return_value, ans)

    def test_update(self):
        um = self.conn.__getitem__.return_value.update_many

        sql = 'UPDATE "table" SET "col1" = %s, "col2" = NULL WHERE "table"."col2" = %s'
        params = [1, 2]
        result = Result(self.db, self.conn, self.conn_prop, sql, params)
        um.assert_any_call(filter={'col2': {'$eq': 2}}, update={'$set': {'col1': 1, 'col2': None}})
        self.conn.reset_mock()

        sql = 'UPDATE "table" SET "col" = %s WHERE "table"."col" = %s'
        params = [1,2]
        result = Result(self.db, self.conn, self.conn_prop, sql, params)
        um.assert_any_call(filter={'col': {'$eq': 2}}, update={'$set': {'col': 1}})
        self.conn.reset_mock()

        sql = 'UPDATE "table" SET "col1" = %s WHERE "table"."col2" = %s'
        params = [1,2]
        result = Result(self.db, self.conn, self.conn_prop, sql, params)
        um.assert_any_call(filter={'col2': {'$eq': 2}}, update={'$set': {'col1': 1}})
        self.conn.reset_mock()

        sql = 'UPDATE "table" SET "col1" = %s, "col2" = %s WHERE "table"."col2" = %s'
        params = [1, 2, 3]
        result = Result(self.db, self.conn, self.conn_prop, sql, params)
        um.assert_any_call(filter={'col2': {'$eq': 3}}, update={'$set': {'col1': 1, 'col2': 2}})
        self.conn.reset_mock()

    def test_insert(self):
        io = self.conn.__getitem__.return_value.insert_many

        sql = 'INSERT INTO "table" ("col1", "col2") VALUES (%s, %s)'
        params = [1, 2]
        result = Result(self.db, self.conn, self.conn_prop, sql, params)
        io.assert_any_call([{'col1':1, 'col2': 2}], ordered=False)
        self.conn.reset_mock()

        sql = 'INSERT INTO "table" ("col1", "col2") VALUES (%s, NULL)'
        params = [1]
        result = Result(self.db, self.conn, self.conn_prop, sql, params)
        io.assert_any_call([{'col1': 1, 'col2': None}], ordered=False)
        self.conn.reset_mock()

        sql = 'INSERT INTO "table" ("col") VALUES (%s)'
        params = [1]
        result = Result(self.db, self.conn, self.conn_prop, sql, params)
        io.assert_any_call([{'col': 1}], ordered=False)
        self.conn.reset_mock()

        #INSERT INTO "m2m_regress_post" ("id") VALUES (DEFAULT)
        sql = 'INSERT INTO "table" ("id") VALUES (DEFAULT)'
        params = []
        aid = MagicMock()
        auto = {
            'auto': {
                'field_names': ['id'],
                'seq': 1
            }
        }
        self.conn.__getitem__().find_one_and_update.return_value = auto

        result = Result(self.db, self.conn, self.conn_prop, sql, params)

        io.assert_any_call([{'id': 1}], ordered=False)
        self.conn.reset_mock()


    @skip
    def test_statement(self):
        """
        'SELECT * FROM table'
        :return:
        """
        'SELECT "t"."c1" AS Col1, "t"."c2", COUNT("t"."c3") AS "c3__count" FROM "table"'

        self.sql = 'UPDATE "table" SET "col" = %s WHERE "table"."col1" = %s'
        self.params = [1, 2]
        self.it
        self.find_mock()
        find = self.find

    def test_groupby(self):
        t1c1 = '"table1"."col1"'
        t1c2 = '"table1"."col2"'
        t1c3 = '"table1"."col3"'
        t2c2 = '"table2"."col2"'

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
        ans = [('a1', 'a2',1,2), ('b1', 'b2',3,4)]
        self.aggregate_mock(pipeline, return_value, ans)


        self.sql = (
            f'SELECT {t1c1}, {t1c2}, MIN({t2c2}) AS "dt" '
            f'FROM table1 '
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
        self.aggregate_mock(pipeline, return_value, ans)

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
                '$match': {'dt' : {'$lt': 2}}
            }
        ]
        self.aggregate_mock(pipeline, return_value, ans)

    @skip
    def test_special(self):
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
        ret = self.find_mock()
        self.assertEqual(ret, [(1,)])
        self.find.assert_any_call(**find_args)
        self.conn.reset_mock()

    def test_in(self):
        conn = self.conn
        find = self.find
        iter = self.iter

        t1c1 = '"table1"."col1"'

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
        ans = self.find_mock()
        find.assert_any_call(**find_args)
        self.assertEqual(ans, [(1,2), (3,4)])
        conn.reset_mock()

        # TODO: This is not the right SQL syntax
        self.sql = f'{where} {t1c1} IN (NULL, %s)'
        find_args['filter'] = {
            'col1': {
                '$in': [None, 1]
            }
        }
        self.params = [1]
        iter.return_value = [{'_id': 'x', 'col1': 1, 'col2': 2}, {'_id': 'x', 'col1': 3, 'col2': 4}]
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} {t1c1} IN (NULL)'
        find_args['filter'] = {
            'col1': {
                '$in': [None]
            }
        }
        self.params = []
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} {t1c1} NOT IN (%s)'
        find_args['filter'] = {
            'col1': {
                '$nin': [1]
            }
        }
        self.params = [1]
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} {t1c1} NOT IN (%s, %s)'
        find_args['filter'] = {
            'col1': {
                '$nin': [1, 2]
            }
        }
        self.params = [1, 2]
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} NOT ({t1c1} IN (%s))'
        find_args['filter'] = {
            'col1': {
                '$nin': [1]
            }
        }
        self.params = [1]
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_join(self):
        """
         sql_command: SELECT "null_fk_comment"."id", "null_fk_comment"."post_id", "null_fk_comment"."comment_text", "null_fk_post"."id", "null_fk_post"."forum_id", "null_fk_post"."title", "null_fk_forum"."id", "null_fk_forum"."system_info_id", "null_fk_forum"."forum_name", "null_fk_systeminfo"."id", "null_fk_systeminfo"."system_details_id", "null_fk_systeminfo"."system_name" FROM "null_fk_comment" LEFT OUTER JOIN "null_fk_post" ON ("null_fk_comment"."post_id" = "null_fk_post"."id") LEFT OUTER JOIN "null_fk_forum" ON ("null_fk_post"."forum_id" = "null_fk_forum"."id") LEFT OUTER JOIN "null_fk_systeminfo" ON ("null_fk_forum"."system_info_id" = "null_fk_systeminfo"."id") ORDER BY "null_fk_comment"."comment_text" ASC
        :return:
        """
        t1c1 = '"table1"."col1"'
        t2c1 = '"table2"."col1"'
        t4c1 = '"table4"."col1"'

        t1c2 = '"table1"."col2"'
        t2c2 = '"table2"."col2"'
        t3c2 = '"table3"."col2"'
        t3c1 = '"table3"."col1"'

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
        self.aggregate_mock(pipeline, return_value, ans)

    def test_nested_in(self):

        t1c1 = '"table1"."col1"'
        t1c2 = '"table1"."col2"'
        t2c1 = '"table2"."col1"'
        t2c2 = '"table2"."col2"'
        return_value = [{'col1': 'a1', 'col2': 'a2'}, {'col1': 'b1', 'col2': 'b2'}]
        ans = [('a1', 'a2'),('b1', 'b2')]

        self.sql = f'SELECT {t1c1}, {t1c2} FROM "table1" WHERE ({t1c1} IN (SELECT {t2c1} FROM "table2" U0 WHERE (U0."col2" IN (%s, %s))))'
        self.params = [1,2]
        inner_pipeline = [
            {
                '$match': {
                    'col2': {
                        '$in': [1,2]
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
        self.aggregate_mock(pipeline, return_value, ans)

        self.sql = f'SELECT {t1c1}, {t1c2} FROM "table1" WHERE {t1c1} IN (SELECT U0."col1" AS Col1 FROM "table2" U0 INNER JOIN "table1" U1 ON (U0."col1" = U1."col1") WHERE (U1."col2" IN (%s, %s))) ORDER BY {t1c2} DESC'

        self.params = [1,2,3,4,5]
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
                        '$in': [1,2]
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
        self.aggregate_mock(pipeline, return_value, ans)



    def test_not(self):
        conn = self.conn
        find = self.find

        t1c1 = '"table"."col1"'

        # Testing for different combinations 'where' syntax
        # from here on

        where = 'SELECT "table"."col" FROM "table" WHERE'
        find_args = {
            'projection': ['col'],
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
        self.iter.return_value = [{'_id': 'x', 'col': 1}, {'_id': 'x', 'col': 3,}]
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} NOT {t1c1} <= %s'
        find_args['filter'] = {
            'col1': {
                '$not': {
                    '$lte': 1
                }
            }
        }
        self.params = [1]
        self.iter.return_value = [{'_id': 'x', 'col': 1}, {'_id': 'x', 'col': 3,}]
        self.find_mock()
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
        self.iter.return_value = [{'_id': 'x', 'col': 1}, {'_id': 'x', 'col': 3, }]
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()


    def test_basic(self):
        conn = self.conn
        find = self.find

        t1c1 = '"table"."col1"'

        # Testing for different combinations 'where' syntax
        # from here on

        where = 'SELECT "table"."col" FROM "table" WHERE'
        find_args = {
            'projection': ['col'],
            'filter': {}
        }

        self.sql = f'{where} {t1c1} = %s'
        find_args['filter'] = {
            'col1': {
                '$eq': 1
            }
        }
        self.params = [1]
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} {t1c1} <= %s'
        find_args['filter'] = {
            'col1': {
                '$lte': 1
            }
        }
        self.params = [1]
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} {t1c1} = NULL'
        find_args['filter'] = {
            'col1': {
                '$eq': None
            }
        }
        self.params = []
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_and_or(self):
        conn = self.conn
        find = self.find

        t1c1 = '"table"."col1"'
        t1c2 = '"table"."col2"'

        where = 'SELECT "table"."col" FROM "table" WHERE'
        find_args = {
            'projection': ['col'],
            'filter': {}
        }

        # Testing for different combinations 'where' syntax
        # from here on

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
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

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
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

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
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

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
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

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
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

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
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

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
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

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
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

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
        self.find_mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        # WHERE "admin_changelist_event"."event_date" BETWEEN %(0)s AND %(1)s'
        self.sql = f'{where} ({t1c1} BETWEEN %s AND %s)'
        find_args['filter'] = {'col1': {'$gte': 1, '$lte': 2}}
        self.params = [1, 2]
        self.find_mock()
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
        self.assertEqual(params['enforce_schema'], True)

    def test_connection_params(self):
        """Check for returned connection params if filled settings dict is provided"""
        name = MagicMock()
        port = MagicMock()
        host = MagicMock()

        settings_dict = {
                'NAME': name,
                'PORT': port,
                'HOST': host
        }

        wrapper = DatabaseWrapper(settings_dict)

        params = wrapper.get_connection_params()

        assert params['name'] is name
        assert params['port'] is port
        assert params['host'] is host

    @patch('djongo.database.MongoClient')
    def test_connection(self, mocked_mongoclient):
        settings_dict = MagicMock(dict)
        wrapper = DatabaseWrapper(settings_dict)

        wrapper.get_new_connection(wrapper.get_connection_params())

        mocked_mongoclient.assert_called_once()