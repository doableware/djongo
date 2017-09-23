from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.base.client import BaseDatabaseClient
from django.db.backends.base.creation import BaseDatabaseCreation
from django.db.utils import Error
from .introspection import DatabaseIntrospection
from pymongo import MongoClient

from .operations import DatabaseOperations
from .schema import DatabaseSchemaEditor
from .cursor import Cursor
from .features import DatabaseFeatures
from . import database


class DatabaseWrapper(BaseDatabaseWrapper):

    data_types = {
        'AutoField': 'integer',
        'BigAutoField': 'integer',
        'BinaryField': 'integer',
        'BooleanField': 'bool',
        'CharField': 'char',
        'CommaSeparatedIntegerField': 'char',
        'DateField': 'date',
        'DateTimeField': 'datetime',
        'DecimalField': 'float',
        'DurationField': 'integer',
        'FileField': 'char',
        'FilePathField': 'char',
        'FloatField': 'float',
        'IntegerField': 'integer',
        'BigIntegerField': 'bigint',
        'IPAddressField': 'char',
        'GenericIPAddressField': 'char',
        'NullBooleanField': 'bool',
        'OneToOneField': 'integer',
        'PositiveIntegerField': 'integer',
        'PositiveSmallIntegerField': 'integer',
        'SlugField': 'char',
        'SmallIntegerField': 'integer',
        'TextField': 'char',
        'TimeField': 'time',
        'UUIDField': 'char',
    }

    data_types_suffix = {
        'AutoField': 'AUTOINCREMENT',
        'BigAutoField': 'AUTOINCREMENT',
    }

    operators = {
        'exact': '= %s',
        'iexact': 'LIKE %s',
        'contains': 'LIKE BINARY %s',
        'icontains': 'LIKE %s',
        'regex': 'REGEXP BINARY %s',
        'iregex': 'REGEXP %s',
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': 'LIKE BINARY %s',
        'endswith': 'LIKE BINARY %s',
        'istartswith': 'LIKE %s',
        'iendswith': 'LIKE %s',
    }

    vendor = 'djongo'
    SchemaEditorClass = DatabaseSchemaEditor
    Database = database

    client_class = BaseDatabaseClient
    creation_class = BaseDatabaseCreation
    features_class = DatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

    def is_usable(self):
        if self.connection is not None:
            return True
        return False

    def get_connection_params(self):
        # TODO: Add other parameters here
        settings_dict = {}

        settings_dict['name'] = self.settings_dict.get('NAME', 'djongo_test')
        settings_dict['host'] = self.settings_dict.get('HOST', 'localhost')
        settings_dict['port'] = self.settings_dict.get('PORT', 27017)

        return settings_dict

    def get_new_connection(self, settings_dict):
        """
        This needs to be made more generic to accept
        other MongoClient parameters.
        """
        name = settings_dict.pop('name')
        return MongoClient(**settings_dict)[name]

    def _set_autocommit(self, autocommit):
        pass

    def init_connection_state(self):
        pass

    def create_cursor(self, name=None):
        return Cursor(self.connection)

    def _close(self):
        if self.connection:
            with self.wrap_database_errors:
                self.connection.client.close()

    def _rollback(self):
        raise Error

    def _commit(self):
        pass
