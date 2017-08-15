from django.db.backends.base.introspection import BaseDatabaseIntrospection


class DatabaseIntrospection(BaseDatabaseIntrospection):
    def table_names(self, cursor=None, include_views=False):
        return sorted(cursor.m_cli_connection.collection_names(False))

    def get_table_list(self, cursor):
        return cursor.m_cli_connection.collection_names()
