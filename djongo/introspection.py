import collections
import datetime

import bson
from django.db.backends.base.introspection import BaseDatabaseIntrospection, FieldInfo, TableInfo
from django.db.models import Index


class DatabaseIntrospection(BaseDatabaseIntrospection):
    SAMPLE_SIZE = 10000
    TYPE_MAPPING = {
        int: bson.int64.Int64,
    }

    data_types_reverse = {
        bson.int64.Int64: 'BigIntegerField',
        bson.objectid.ObjectId: 'ObjectIdField',
        collections.OrderedDict: 'JSONField',
        datetime.date: 'DateField',
        datetime.datetime: 'DateTimeField',
        bool: 'BooleanField',
        dict: 'JSONField',
        float: 'FloatField',
        int: 'IntegerField',
        list: 'JSONField',
        str: 'CharField',
        'text': 'TextField',
        'int64': 'BigIntegerField',
        'int32': 'IntegerField',
        'number': 'DecimalField',
        'string': 'CharField',
        'boolean': 'BooleanField',
        'object': 'djongo.models.DictField',
        'array': 'djongo.models.ListField',
        'oid': 'djongo.models.ObjectIdField',
        'date': 'DateTimeField'

    }

    # def table_names(self, cursor=None, include_views=False):
    #     return sorted(cursor.m_cli_connection.collection_names(False))

    def get_table_list(self, cursor):

        return [
            TableInfo(c, 't')
            for c in cursor.db_conn.list_collection_names()
            if c != '__schema__'
        ]

    def get_constraints(self, cursor, table_name):
        constraint = {}

        indexes = cursor.db_conn[table_name].index_information()
        for name, info in indexes.items():
            if name == '_id_':
                continue

            columns = [field[0] for field in info['key']]
            orders = ['ASC' if field[1] == 1 else 'DESC'
                      for field in info['key']]
            constraint[name] = {
                'columns': columns,
                'primary_key': name == '__primary_key__',
                'unique': info.get('unique', False),
                'index': True,
                'orders': orders,
                "foreign_key": False,
                "check": False,
                'type': Index.suffix
            }
        return constraint

    def get_key_columns(self, cursor, table_name):
        return []

    def get_indexes(self, cursor, table_name):
        return self.get_constraints(cursor, table_name)

    def get_relations(self, cursor, table_name):
        return []

    def get_sequences(self, cursor, table_name, table_fields=()):
        pk_col = self.get_primary_key_column(cursor, table_name)
        return [{'table': table_name, 'column': pk_col}]

    def get_table_description(self, cursor, table_name):
        colspecs = collections.defaultdict(lambda: dict(
            types=collections.Counter(),
            specs=collections.defaultdict(int),
        ))
        fields = cursor.db_conn['__schema__'].find_one(
            {'name': table_name},
            {'fields': True}
        )['fields']
        columns = []
        for name, properties in fields.items():
            columns.append(
                FieldInfo(
                    name=name,
                    type_code=properties['type_code'],
                    display_size=None,
                    internal_size=None,
                    precision=None,
                    scale=None,
                    null_ok=None,
                    default=None
                )
            )
        return columns
        results = cursor.db_conn[table_name].aggregate([
            {'$sample': {'size': self.SAMPLE_SIZE}},
        ])
        for result in results:
            for k, v in result.items():
                column = colspecs[k]
                specs = column['specs']

                column['types'][type(v)] += 1

                if isinstance(v, str):
                    specs['length'] = max(specs['length'], len(str(v)))

                if isinstance(v, (int, bson.int64.Int64, float)):
                    specs['max_value'] = max(specs['max_value'], v)

                if isinstance(v, float):
                    # Convert to string and count the characters after the .
                    precision = len(str(v).split('.')[1])
                    specs['precision'] = max(specs['precision'], precision)

        columns = []
        for name, column in colspecs.items():
            types = column['types']
            specs = column['specs']

            if type(None) in types:
                nullable = True
                del types[type(None)]
            else:
                nullable = False

            for from_, count in list(types.items()):
                to = self.TYPE_MAPPING.get(from_)
                if to:
                    types[to] = types.pop(from_)

            type_ = types.most_common(1)[0][0]
            if type_ == str and specs['length'] > 200:
                type_ = 'text'
                del specs['length']

            if len(types) > 1:
                print('# Found multiple types for %s.%s: %s' %
                      (table_name, name, types))

            columns.append(FieldInfo(
                name,  # name
                type_,  # type_code
                specs.get('length'),  # display size
                specs.get('length'),  # internal size
                specs.get('precision'),  # precision
                None,  # scale
                nullable,  # nullable
                None,  # default
            ))

        return columns
