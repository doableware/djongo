import bson
import datetime
import collections

from django.db.backends.base import introspection


class DatabaseIntrospection(introspection.BaseDatabaseIntrospection):
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
    }

    def get_table_list(self, cursor):
        '''Return a list of MongDB collections (tables)'''
        return [introspection.TableInfo(c, 't')
                for c in cursor.db_conn.collection_names(False)]

    def get_constraints(self, cursor, table_name):
        '''
        Retrieve any constraints or keys (unique, pk, fk, check, index)
        across one or more columns. Since MongoDB doesn't really support
        foreign keys this will only ever return unique constraints and primary
        keys
        '''
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
            }
        return constraint

    def get_key_columns(self, cursor, table_name):
        '''Key columns are not supported so this always returns `[]`'''
        return []

    def get_indexes(self, cursor, table_name):
        '''Effectively an alias for `get_constraints`'''
        return self.get_constraints(cursor, table_name)

    def get_relations(self, cursor, table_name):
        '''Relations are not supported so this always returns `[]`'''
        return []

    def get_table_description(self, cursor, table_name):
        '''
        Get a colletction description by fetching a sample of `SAMPLE_SIZE` and
        analyzing it's contents. Because MongoDB doesn't have a fixed document
        specification this is only an approximation but depending on the
        `SAMPLE_SIZE` relative to the collection size it can be rather
        accurate.
        '''
        colspecs = collections.defaultdict(lambda: dict(
            types=collections.Counter(),
            specs=collections.defaultdict(int),
        ))

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

            columns.append(introspection.FieldInfo(
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
