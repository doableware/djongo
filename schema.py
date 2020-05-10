from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from logging import getLogger

logger = getLogger(__name__)


class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):

    sql_create_index = "ALTER TABLE %(table)s ADD CONSTRAINT %(name)s INDEX (%(columns)s)%(extra)s"
    sql_delete_index = "ALTER TABLE %(table)s DROP CONSTRAINT %(name)s INDEX"


    def quote_value(self, value):
        return value

    def prepare_default(self, value):
        raise NotImplementedError()

