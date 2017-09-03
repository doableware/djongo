
from pymongo import MongoClient
from djongo.cursor import Parse

sql = 'SELECT "django_migrations"."app", "django_migrations"."trial"\
FROM  "django_migrations" WHERE ("django_migrations"."app" <=%s AND \
"django_migrations"."trial" >=%s AND "django_migrations"."app" >=%s) OR ("django_migrations"."app" <=%s AND \
"django_migrations"."app">%s)'

sql = 'SELECT "auth_permission"."content_type_id", "auth_permission"."codename"\
   FROM "auth_permission" INNER JOIN "django_content_type" \
   ON ("auth_permission"."content_type_id" = "django_content_type"."id")\
   WHERE "auth_permission"."content_type_id" IN (%s, %s) \
   ORDER BY "django_content_type"."app_label" ASC,\
   "django_content_type"."model" ASC, "auth_permission"."codename" ASC'

sql = 'SELECT "django_content_type"."id", "django_content_type"."app_label",\
   "django_content_type"."model" FROM "django_content_type" \
   WHERE ("django_content_type"."model" = %s AND "django_content_type"."app_label" = %s)'

sql = 'SELECT (1) AS "a" FROM "django_session" WHERE "django_session"."session_key" = %(0)s LIMIT 1'

sql = 'DELETE FROM "django_session" WHERE "django_session"."session_key" IN (%(0)s)'
sql = 'UPDATE "django_session" SET "session_data" = %(0)s, "expire_date" = %(1)s WHERE "django_session"."session_key" = %(2)s'
sql = 'SELECT "django_admin_log"."id", "django_admin_log"."action_time",\
   "django_admin_log"."user_id", "django_admin_log"."content_type_id",\
   "django_admin_log"."object_id", "django_admin_log"."object_repr", \
   "django_admin_log"."action_flag", "django_admin_log"."change_message",\
   "auth_user"."id", "auth_user"."password", "auth_user"."last_login", \
   "auth_user"."is_superuser", "auth_user"."username", "auth_user"."first_name",\
   "auth_user"."last_name", "auth_user"."email", "auth_user"."is_staff",\
   "auth_user"."is_active", "auth_user"."date_joined", "django_content_type"."id",\
   "django_content_type"."app_label", "django_content_type"."model"\
   FROM "django_admin_log" INNER JOIN "auth_user" \
   ON ("django_admin_log"."user_id" = "auth_user"."id")\
   LEFT OUTER JOIN "django_content_type" ON ("django_admin_log"."content_type_id" = "django_content_type"."id")\
   WHERE "django_admin_log"."user_id" = %(0)s ORDER BY "django_admin_log"."action_time" DESC LIMIT 10'

db = MongoClient()['django-db']
test = Parse(db, sql, [1, 2, 3, 4, 5])
cur = test.get_mongo_cur()

print(cur.count())