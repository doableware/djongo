from io import StringIO

from django.core.management import call_command
from django.test.utils import modify_settings

from . import PostgreSQLTestCase


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class InspectDBTests(PostgreSQLTestCase):
    def assertFieldsInModel(self, model, field_outputs):
        out = StringIO()
        call_command(
            'inspectdb',
            table_name_filter=lambda tn: tn.startswith(model),
            stdout=out,
        )
        output = out.getvalue()
        for field_output in field_outputs:
            self.assertIn(field_output, output)

    def test_json_field(self):
        self.assertFieldsInModel(
            'postgres_tests_jsonmodel',
            ['field = django.contrib.postgresql.fields.JSONField(blank=True, null=True)'],
        )

    def test_range_fields(self):
        self.assertFieldsInModel(
            'postgres_tests_rangesmodel',
            [
                'ints = django.contrib.postgresql.fields.IntegerRangeField(blank=True, null=True)',
                'bigints = django.contrib.postgresql.fields.BigIntegerRangeField(blank=True, null=True)',
                'floats = django.contrib.postgresql.fields.FloatRangeField(blank=True, null=True)',
                'timestamps = django.contrib.postgresql.fields.DateTimeRangeField(blank=True, null=True)',
                'dates = django.contrib.postgresql.fields.DateRangeField(blank=True, null=True)',
            ],
        )
