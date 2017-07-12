from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.base.validation import BaseDatabaseValidation
from django.db.backends.base.client import BaseDatabaseClient
from django.db.backends.base.creation import BaseDatabaseCreation
from django.db.backends.base.features import BaseDatabaseFeatures
from django.db.utils import Error
from .introspection import DatabaseIntrospection
from pymongo import MongoClient
import pymongo, os

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

   def get_connection_params(self):
      if not self.settings_dict['NAME']:         
         from django.core.exceptions import ImproperlyConfigured
         raise ImproperlyConfigured(
            "settings.DATABASES is improperly configured. "
            "Please supply the NAME value.")      
      return self.settings_dict['NAME']
   
   def get_new_connection(self, db_name):  
      return MongoClient()[db_name]
      #if os.name == 'nt':
         #return MongoClient(port=27016)[db_name]
      #else:
         #return MongoClient()[db_name]
      
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
   
   #def is_usable(self):
      #a = MongoClient()
      #a.is_locked
      #self.connection