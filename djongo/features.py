from django.db.backends.base.features import BaseDatabaseFeatures


class DatabaseFeatures(BaseDatabaseFeatures):
    supports_transactions = False
    # djongo doesn't seem to support this currently
    has_bulk_insert = True
    has_native_uuid_field = True
    supports_timezones = False
    uses_savepoints = False
    can_clone_databases = True
    test_db_allows_multiple_connections = False
    supports_unspecified_pk = True

    # Django 3.1+ features
    supports_json_field = True

    # Django 4.0+ features
    supports_expression_defaults = False
    supports_table_check_constraints = False
    supports_column_check_constraints = False
    can_return_columns_from_insert = False
    can_return_rows_from_bulk_insert = False

    # Django 4.1+ features
    supports_comments = False
    supports_comments_inline = False

