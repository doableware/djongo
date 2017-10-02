from unittest import TestCase, mock

from logging import getLogger, DEBUG, StreamHandler
from pymongo import MongoClient
from djongo.sql2mongo import Parse

sql = [
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
WHERE "auth_permission"."content_type_id" IN (%s, %s) \
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

'SELECT "auth_group_permissions"."permission_id" FROM "auth_group_permissions" WHERE ("auth_group_permissions"."group_id" = %s AND "auth_group_permissions"."permission_id" IN (%s))'

       ]

root_logger = getLogger()
root_logger.setLevel(DEBUG)
root_logger.addHandler(StreamHandler())

class TestParse(TestCase):

    def test_parse(self):
        conn = MongoClient()['djongo-test']
        for s in sql:
            result = Parse(conn, s, [1, 2, 3, 4, 5]).result()
            try:
                doc = result.next()
            except StopIteration:
                pass