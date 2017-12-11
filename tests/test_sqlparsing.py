from unittest import TestCase, mock

from logging import getLogger, DEBUG, StreamHandler
from pymongo import MongoClient
from pymongo.cursor import Cursor

from djongo.sql2mongo import Parse

sql = [
    'UPDATE "auth_user" SET "password" = %s, "last_login" = NULL, "is_superuser" = %s, "username" = %s, "first_name" = %s, "last_name" = %s, "email" = %s, "is_staff" = %s, "is_active" = %s, "date_joined" = %s WHERE "auth_user"."id" = %s',

'CREATE TABLE "django_migrations" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "app" char NOT NULL, "name" char NOT NULL, "applied" datetime NOT NULL)',

'SELECT "django_migrations"."app", "django_migrations"."trial" '
'FROM  "django_migrations" '
'WHERE ("django_migrations"."app" <=%s '
      'AND "django_migrations"."trial" >=%s '
      'AND "django_migrations"."app" >=%s) '
      'OR ("django_migrations"."app" <=%s '
      'AND "django_migrations"."app">%s)',

'SELECT "auth_permission"."content_type_id", "auth_permission"."codename" \
FROM "auth_permission" INNER JOIN "django_content_type" \
    ON ("auth_permission"."content_type_id" = "django_content_type"."id") \
WHERE "auth_permission"."content_type_id" IN (%(0)s, %(1)s) \
ORDER BY "django_content_type"."app_label" ASC,\
"django_content_type"."model" ASC, "auth_permission"."codename" ASC',

'SELECT "django_content_type"."id", "django_content_type"."app_label",\
"django_content_type"."model" FROM "django_content_type" \
WHERE ("django_content_type"."model" = %s AND "django_content_type"."app_label" = %s)',

'SELECT (1) AS "a" FROM "django_session" WHERE "django_session"."session_key" = %(0)s LIMIT 1',

'SELECT COUNT(*) AS "__count" FROM "auth_user"',

'DELETE FROM "django_session" WHERE "django_session"."session_key" IN (%(0)s)',

'UPDATE "django_session" SET "session_data" = %(0)s, "expire_date" = %(1)s WHERE "django_session"."session_key" = %(2)s',

'SELECT "django_admin_log"."id", "django_admin_log"."action_time",\
    "django_admin_log"."user_id", "django_admin_log"."content_type_id",\
    "django_admin_log"."object_id", "django_admin_log"."object_repr", \
    "django_admin_log"."action_flag", "django_admin_log"."change_message",\
    "auth_user"."id", "auth_user"."password", "auth_user"."last_login", \
    "auth_user"."is_superuser", "auth_user"."username", "auth_user"."first_name",\
    "auth_user"."last_name", "auth_user"."email", "auth_user"."is_staff",\
    "auth_user"."is_active", "auth_user"."date_joined", "django_content_type"."id",\
    "django_content_type"."app_label", "django_content_type"."model" \
FROM "django_admin_log" \
INNER JOIN "auth_user" \
    ON ("django_admin_log"."user_id" = "auth_user"."id") \
LEFT OUTER JOIN "django_content_type" \
    ON ("django_admin_log"."content_type_id" = "django_content_type"."id") \
WHERE "django_admin_log"."user_id" = %(0)s ORDER BY "django_admin_log"."action_time" DESC LIMIT 10',

'SELECT "auth_permission"."id", "auth_permission"."name", "auth_permission"."content_type_id", "auth_permission"."codename" '
'FROM "auth_permission" '
'INNER JOIN "auth_user_user_permissions" '
    'ON ("auth_permission"."id" = "auth_user_user_permissions"."permission_id") '
'INNER JOIN "django_content_type" '
    'ON ("auth_permission"."content_type_id" = "django_content_type"."id") '
'WHERE "auth_user_user_permissions"."user_id" = %s '
'ORDER BY "django_content_type"."app_label" ASC, "django_content_type"."model" ASC, "auth_permission"."codename" ASC',

'SELECT "auth_permission"."id", "auth_permission"."name", "auth_permission"."content_type_id", '
    '"auth_permission"."codename", "django_content_type"."id", "django_content_type"."app_label", "django_content_type"."model" '
'FROM "auth_permission" '
'INNER JOIN "django_content_type" '
    'ON ("auth_permission"."content_type_id" = "django_content_type"."id") '
'ORDER BY "django_content_type"."app_label" ASC, "django_content_type"."model" ASC, "auth_permission"."codename" ASC',

'SELECT "django_admin_log"."id", "django_admin_log"."action_time", "django_admin_log"."user_id", "django_admin_log"."content_type_id", "django_admin_log"."object_id", "django_admin_log"."object_repr", "django_admin_log"."action_flag", "django_admin_log"."change_message", "auth_user"."id", "auth_user"."password", "auth_user"."last_login", "auth_user"."is_superuser", "auth_user"."username", "auth_user"."first_name", "auth_user"."last_name", "auth_user"."email", "auth_user"."is_staff", "auth_user"."is_active", "auth_user"."date_joined", "django_content_type"."id", "django_content_type"."app_label", "django_content_type"."model" FROM "django_admin_log" INNER JOIN "auth_user" ON ("django_admin_log"."user_id" = "auth_user"."id") LEFT OUTER JOIN "django_content_type" ON ("django_admin_log"."content_type_id" = "django_content_type"."id") WHERE "django_admin_log"."user_id" = %(0)s ORDER BY "django_admin_log"."action_time" DESC LIMIT 10',

'SELECT "auth_permission"."id" FROM "auth_permission" INNER JOIN "auth_group_permissions" ON ("auth_permission"."id" = "auth_group_permissions"."permission_id") INNER JOIN "django_content_type" ON ("auth_permission"."content_type_id" = "django_content_type"."id") WHERE "auth_group_permissions"."group_id" = %s ORDER BY "django_content_type"."app_label" ASC, "django_content_type"."model" ASC, "auth_permission"."codename" ASC',

'SELECT "auth_group_permissions"."permission_id" FROM "auth_group_permissions" WHERE ("auth_group_permissions"."group_id" = %s AND "auth_group_permissions"."permission_id" IN (%s))',

'SELECT (1) AS "a" FROM "auth_group" WHERE ("auth_group"."name" = %(0)s AND NOT ("auth_group"."id" = %(1)s)) LIMIT 1',

'SELECT DISTINCT "viewflow_task"."flow_task" FROM "viewflow_task" INNER JOIN "viewflow_process" ON ("viewflow_task"."process_id" = "viewflow_process"."id") WHERE ("viewflow_process"."flow_class" IN (%(0)s, %(1)s, %(2)s) AND "viewflow_task"."owner_id" = %(3)s AND "viewflow_task"."status" = %(4)s) ORDER BY "viewflow_task"."flow_task" ASC'

'SELECT DISTINCT "table1"."col1" FROM "table1" INNER JOIN "table2" ON ("table1"."col2" = "table2"."col1") WHERE ("table2"."flow_class" IN (%(0)s, %(1)s, %(2)s) AND "table1"."col3" = %(3)s AND "table1"."col4" = %(4)s) ORDER BY "table1"."col1" ASC',

'SELECT "dummy_multipleblogposts"."id", "dummy_multipleblogposts"."h1", "dummy_multipleblogposts"."content" FROM "dummy_multipleblogposts" WHERE "dummy_multipleblogposts"."h1" IN (SELECT U0."id" AS Col1 FROM "dummy_blogpost" U0 WHERE U0."h1" IN (%s, %s))'
       ]

root_logger = getLogger()
root_logger.setLevel(DEBUG)
root_logger.addHandler(StreamHandler())


class TestParse(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.conn = mock.MagicMock()
        cls.db = mock.MagicMock()
        cls.find = cls.conn.__getitem__().find
        cursor = mock.MagicMock()
        cursor.__class__ = Cursor
        cursor.count.return_value =1
        cls.find.return_value = cursor

        cls.distinct = cursor.distinct
        cursor2 = mock.MagicMock()
        cursor2.__class__ = Cursor
        cls.distinct.return_value = cursor2

    def _mock(self):
        result = Parse(self.db, self.conn, self.sql, self.params).result()
        doc = next(result)

    def test_statement(self):
        """
        'SELECT * FROM table'
        :return:
        """
        'SELECT "t"."c1" AS Col1, "t"."c2", COUNT("t"."c3") AS "c3__count" FROM "table"'
        'SELECT COUNT(*) AS "__count" FROM "table"'
        self.sql = 'SELECT "t"."c1" AS Col1, "t"."c2", COUNT("t"."c3") AS "c3__count" FROM "table"'
        self.params = [1]
        self._mock()
        find = self.find


    def test_special(self):
        """
        SELECT "dummy_multipleblogposts"."id", "dummy_multipleblogposts"."h1", "dummy_multipleblogposts"."content", COUNT("dummy_multipleblogposts"."h1") AS "h1__count", COUNT("dummy_multipleblogposts"."content") AS "content__count" FROM "dummy_multipleblogposts" GROUP BY "dummy_multipleblogposts"."id", "dummy_multipleblogposts"."h1", "dummy_multipleblogposts"."content" LIMIT 21



        :return:
        """


        conn = self.conn
        find = self.find
        distinct = self.distinct

        # Test for special cases of sql syntax first
        self.sql = 'SELECT DISTINCT "table1"."col1" FROM "table1" WHERE "table1"."col2" = %s'
        self.params = [1]
        find_args = {
            'projection': ['col1'],
            'filter': {
                'col2': {
                    '$eq': 1
                }
            }
        }

        self._mock()
        find.assert_any_call(**find_args)
        distinct.assert_any_call('col1')
        conn.reset_mock()

        # 'SELECT (1) AS "a" FROM "django_session" WHERE "django_session"."session_key" = %(0)s LIMIT 1'
        self.sql = 'SELECT (1) AS "a" FROM "table" WHERE "table1"."col2" = %s LIMIT 1'
        find_args = {
            'filter': {
                'col1': {
                    '$eq': 1
                }
            },
            'limit': 1
        }
        self.params = [1]
        self._mock()

        find.assert_any_call(**find_args)
        conn.reset_mock()

        #'SELECT COUNT(*) AS "__count" FROM "auth_user"'
        self.sql = 'SELECT COUNT(*) AS "__count" FROM "table"'

        self._mock()
        find.assert_any_call()
        conn.reset_mock()

    def test_in(self):
        conn = self.conn
        find = self.find

        filt_col1 = '"table"."col1"'

        # Testing for different combinations 'where' syntax
        # from here on

        where = 'SELECT "table"."col" FROM "table" WHERE'
        find_args = {
            'projection': ['col'],
            'filter': {}
        }

        self.sql = f'{where} {filt_col1} IN (%s)'
        find_args['filter'] = {
            'col1': {
                '$in': [1]
            }
        }
        self.params = [1]
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        # TODO: This is not the right SQL syntax
        self.sql = f'{where} {filt_col1} IN (NULL, %s)'
        find_args['filter'] = {
            'col1': {
                '$in': [None, 1]
            }
        }
        self.params = [1]
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} {filt_col1} NOT IN (%s)'
        find_args['filter'] = {
            'col1': {
                '$nin': [1]
            }
        }
        self.params = [1]
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} {filt_col1} NOT IN (%s, %s)'
        find_args['filter'] = {
            'col1': {
                '$nin': [1, 2]
            }
        }
        self.params = [1, 2]
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} NOT ({filt_col1} IN (%s))'
        find_args['filter'] = {
            'col1': {
                '$nin': [1]
            }
        }
        self.params = [1]
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        # SELECT "viewflow_process"."id", "viewflow_process"."flow_class", "viewflow_process"."status", "viewflow_process"."created", "viewflow_process"."finished" FROM "viewflow_process" WHERE "viewflow_process"."id" IN (SELECT U0."process_id" AS Col1 FROM "viewflow_task" U0 INNER JOIN "viewflow_process" U1 ON (U0."process_id" = U1."id") WHERE (U1."flow_class" IN (%(0)s, %(1)s, %(2)s) AND U0."owner_id" = %(3)s AND U0."status" = %(4)s)) ORDER BY "viewflow_process"."created" DESC
        where2 = 'SELECT "table2"."col" FROM "table2" WHERE'
        self.sql = f'{where} ({filt_col1} IN ({where2} ({filt_col1} IN (%s))))'
        find_args['filter'] = {
            'col1': {
                '$nin': [1]
            }
        }
        self.params = [1]
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_not(self):
        conn = self.conn
        find = self.find

        filt_col1 = '"table"."col1"'

        # Testing for different combinations 'where' syntax
        # from here on

        where = 'SELECT "table"."col" FROM "table" WHERE'
        find_args = {
            'projection': ['col'],
            'filter': {}
        }

        self.sql = f'{where} NOT ({filt_col1} <= %s)'
        find_args['filter'] = {
            'col1': {
                '$not': {
                    '$lte': 1
                }
            }
        }
        self.params = [1]
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} NOT {filt_col1} <= %s'
        find_args['filter'] = {
            'col1': {
                '$not': {
                    '$lte': 1
                }
            }
        }
        self.params = [1]
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} NOT {filt_col1} = NULL'
        find_args['filter'] = {
            'col1': {
                '$not': {
                    '$eq': None
                }
            }
        }
        self.params = []
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()


    def test_basic(self):
        conn = self.conn
        find = self.find

        filt_col1 = '"table"."col1"'

        # Testing for different combinations 'where' syntax
        # from here on

        where = 'SELECT "table"."col" FROM "table" WHERE'
        find_args = {
            'projection': ['col'],
            'filter': {}
        }

        self.sql = f'{where} {filt_col1} = %s'
        find_args['filter'] = {
            'col1': {
                '$eq': 1
            }
        }
        self.params = [1]
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} {filt_col1} <= %s'
        find_args['filter'] = {
            'col1': {
                '$lte': 1
            }
        }
        self.params = [1]
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} {filt_col1} = NULL'
        find_args['filter'] = {
            'col1': {
                '$eq': None
            }
        }
        self.params = []
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

    def test_and_or(self):
        conn = self.conn
        find = self.find

        filt_col1 = '"table"."col1"'

        # Testing for different combinations 'where' syntax
        # from here on

        where = 'SELECT "table"."col" FROM "table" WHERE'
        find_args = {
            'projection': ['col'],
            'filter': {}
        }

        self.sql = f'{where} ({filt_col1} = %s AND {filt_col1} <= %s)'
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
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} (NOT ({filt_col1} = %s) AND {filt_col1} <= %s)'
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
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} {filt_col1} <= %s AND NOT ({filt_col1} = %s)'
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
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} NOT ({filt_col1} <= %s AND {filt_col1} = %s)'
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
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} NOT ({filt_col1} <= %s OR {filt_col1} = %s)'
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
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()

        self.sql = f'{where} NOT ({filt_col1} <= %s OR {filt_col1} = %s) AND {filt_col1} >= %s'
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
        self._mock()
        find.assert_any_call(**find_args)
        conn.reset_mock()


