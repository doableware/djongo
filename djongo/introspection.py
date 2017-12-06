from django.db.backends.base.introspection import BaseDatabaseIntrospection, TableInfo


class DatabaseIntrospection(BaseDatabaseIntrospection):
    # def table_names(self, cursor=None, include_views=False):
    #     return sorted(cursor.m_cli_connection.collection_names(False))

    def get_table_list(self, cursor):
        return [TableInfo(c,'t') for c in cursor.db_conn.collection_names(False)]

    def get_constraints(self, cursor, table_name):
        constraint = {}

        indexes = cursor.db_conn[table_name].index_information()
        for name, info in indexes.items():
            if name == '_id_':
                continue

            columns = [field[0] for field in info['key']]
            orders = ['ASC' if field[1] == 1 else 'DESC' for field in info['key']]
            constraint[name] = {
                'columns': columns,
                'primary_key': name == '__primary_key__',
                'unique': info.get('unique', False),
                'index': True,
                'orders': orders,
                "foreign_key": False,
                "check": False,
            }
        return constraint

    def get_key_columns(self, cursor, table_name):
        return []

    def get_indexes(self, cursor, table_name):
        return self.get_constraints(cursor, table_name)