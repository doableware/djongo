from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from logging import getLogger

logger = getLogger(__name__)

class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):
    pass
    # def create_model(self, model):
    #     db_con = self.connection.connection
    #     db_con.create_collection(model._meta.db_table)
    #     logger.debug('Created table {}'.format(model._meta.db_table))
    #
    #     for field in model._meta.local_fields:
    #         if field.get_internal_type() in ("AutoField", "BigAutoField"):
    #             db_con['__schema__'].\
    #                 insert_one(
    #                 {
    #                     'name': model._meta.db_table,
    #                     'auto': {
    #                         'field_name': field.column,
    #                         'seq': 0
    #                     }
    #                 }
    #             )
