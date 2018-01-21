"""
MongoDB database backend for Django
"""
from collections import OrderedDict

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.base.client import BaseDatabaseClient
from django.db.backends.base.creation import BaseDatabaseCreation
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.utils import Error
from .introspection import DatabaseIntrospection

from .operations import DatabaseOperations
from .cursor import Cursor
from .features import DatabaseFeatures
from . import database as Database


class DatabaseWrapper(BaseDatabaseWrapper):
    """
    DatabaseWrapper for MongoDB using SQL replacements.
    """

    # This dictionary will map Django model field types to appropriate data
    # types to be used in the database.
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
        'iexact': 'iLIKE %.*s',
        'contains': 'LIKE %s',
        'icontains': 'iLIKE %s',
        'regex': 'REGEXP BINARY %s',
        'iregex': 'REGEXP %s',
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': 'LIKE %s',
        'endswith': 'LIKE %s',
        'istartswith': 'iLIKE %s',
        'iendswith': 'iLIKE %s',
    }

    vendor = 'djongo'
    SchemaEditorClass = BaseDatabaseSchemaEditor
    Database = Database

    client_class = BaseDatabaseClient
    creation_class = BaseDatabaseCreation
    features_class = DatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations

    def __init__(self, *args, **kwargs):
        self.client_conn = None
        super().__init__(*args, **kwargs)

    def is_usable(self):
        if self.connection is not None:
            return True
        return False

    def get_connection_params(self):
        """
        Default method to acquire database connection parameters.

        Sets connection parameters to match settings.py, and sets
        default values to blank fields.
        """
        valid_settings = {
            'NAME': 'name',
            'HOST': 'host',
            'PORT': 'port',
            'USER': 'username',
            'PASSWORD': 'password',
            'AUTH_SOURCE': 'authSource',
            'AUTH_MECHANISM': 'authMechanism'
        }
        connection_params = {
            'name': 'djongo_test'
        }
        for setting_name, kwarg in valid_settings.items():
            try:
                setting = self.settings_dict[setting_name]
            except KeyError:
                continue

            if setting:
                connection_params[kwarg] = setting

        return connection_params


    def get_new_connection(self, connection_params):
        """
        Receives a dictionary connection_params to setup
        a connection to the database.

        Dictionary correct setup is made through the
        get_connection_params method.

        TODO: This needs to be made more generic to accept
        other MongoClient parameters.
        """

        name = connection_params.pop('name')
        connection_params['document_class'] = OrderedDict
        # To prevent leaving unclosed connections behind,
        # client_conn must be closed before a new connection
        # is created.
        if self.client_conn is not None:
            self.client_conn.close()

        self.client_conn = Database.connect(**connection_params)
        return self.client_conn[name]

    def _set_autocommit(self, autocommit):
        """
        Default method must be overridden, eventhough not used.

        TODO: For future reference, setting two phase commits and rollbacks
        might require populating this method.
        """
        pass

    def init_connection_state(self):
        pass

    def create_cursor(self, name=None):
        """
        Returns an active connection cursor to the database.
        """
        return Cursor(self.client_conn, self.connection)

    def _close(self):
        """
        Closes the client connection to the database.
        """
        if self.connection:
            with self.wrap_database_errors:
                self.connection.client.close()

    def _rollback(self):
        raise Error

    def _commit(self):
        """
        Commit routine

        TODO: two phase commits are not supported yet.
        """
        pass
