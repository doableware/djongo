from django.db.backends.base.operations import BaseDatabaseOperations
from django.utils import six
import datetime, calendar


class DatabaseOperations(BaseDatabaseOperations):

    def quote_name(self, name):
        if name.startswith('"') and name.endswith('"'):
            return name
        return '"{}"'.format(name)

    def adapt_datefield_value(self, value):
        if value is None:
            return None
        return datetime.datetime.utcfromtimestamp(calendar.timegm(value.timetuple()))

    def adapt_datetimefield_value(self, value):
        return value

    def adapt_timefield_value(self, value):
        if value is None:
            return None

        if isinstance(value, six.string_types):
            return datetime.datetime.strptime(value, '%H:%M:%S')

        return datetime.datetime(1900, 1, 1, value.hour, value.minute, \
                                 value.second, value.microsecond)

    def convert_datefield_value(self, value, expression, connection, context):
        if isinstance(value, datetime.datetime):
            value = value.date()
        return value

    def convert_timefield_value(self, value, expression, connection, context):
        if isinstance(value, datetime.datetime):
            value = value.time()
        return value

    def get_db_converters(self, expression):
        converters = super(DatabaseOperations, self).get_db_converters(expression)
        internal_type = expression.output_field.get_internal_type()
        if internal_type == 'DateField':
            converters.append(self.convert_datefield_value)
        elif internal_type == 'TimeField':
            converters.append(self.convert_timefield_value)
        return converters

    def sql_flush(self, style, tables, sequences, allow_cascade=False):
        # TODO: Need to implement this fully
        return ['ALTER TABLE']
