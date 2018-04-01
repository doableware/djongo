import sys
import argparse

tests = [
    'absolute_url_overrides', 'admin_autodiscover', 'admin_changelist', 'admin_checks', 'admin_custom_urls', 'admin_default_site', 'admin_docs', 'admin_filters', 'admin_inlines', 'admin_ordering', 'admin_registration', 'admin_scripts', 'admin_utils', 'admin_views', 'admin_widgets', 'aggregation', 'aggregation_regress', 'annotations', 'app_loading', 'apps', 'auth_tests', 'backends', 'base', 'bash_completion', 'basic', 'builtin_server', 'bulk_create', 'cache', 'check_framework', 'choices', 'conditional_processing', 'contenttypes_tests', 'context_processors', 'csrf_tests', 'custom_columns', 'custom_lookups', 'custom_managers', 'custom_methods', 'custom_migration_operations', 'custom_pk', 'datatypes', 'dates', 'datetimes', 'db_functions', 'db_typecasts', 'db_utils', 'dbshell', 'decorators', 'defer', 'defer_regress', 'delete', 'delete_regress', 'deprecation', 'dispatch', 'distinct_on_fields', 'empty', 'expressions', 'expressions_case', 'expressions_window', 'extra_regress', 'field_deconstruction', 'field_defaults', 'field_subclassing', 'file_storage', 'file_uploads', 'files', 'filtered_relation', 'fixtures', 'fixtures_model_package', 'fixtures_regress', 'flatpages_tests', 'force_insert_update', 'foreign_object', 'forms_tests', 'from_db_value', 'generic_inline_admin', 'generic_relations', 'generic_relations_regress', 'generic_views', 'get_earliest_or_latest', 'get_object_or_404', 'get_or_create', 'gis_tests', 'handlers', 'httpwrappers', 'humanize_tests', 'i18n', 'import_error_package', 'indexes', 'inline_formsets', 'inspectdb', 'introspection', 'invalid_models_tests', 'known_related_objects', 'logging_tests', 'lookup', 'm2m_and_m2o', 'm2m_intermediary', 'm2m_multiple', 'm2m_recursive', 'm2m_regress', 'm2m_signals', 'm2m_through', 'm2m_through_regress', 'm2o_recursive', 'mail', 'managers_regress', 'many_to_many', 'many_to_one', 'many_to_one_null', 'max_lengths', 'messages_tests', 'middleware', 'middleware_exceptions', 'migrate_signals', 'migration_test_data_persistence', 'migrations', 'migrations2', 'model_fields', 'model_forms', 'model_formsets', 'model_formsets_regress', 'model_indexes', 'model_inheritance', 'model_inheritance_regress', 'model_meta', 'model_options', 'model_package', 'model_regress', 'modeladmin', 'multiple_database', 'mutually_referential', 'nested_foreign_keys', 'no_models', 'null_fk', 'null_fk_ordering', 'null_queries', 'one_to_one', 'or_lookups', 'order_with_respect_to', 'ordering', 'pagination', 'postgres_tests', 'prefetch_related', 'project_template', 'properties', 'proxy_model_inheritance', 'proxy_models', 'queries', 'queryset_pickle', 'raw_query', 'redirects_tests', 'requests', 'requirements', 'reserved_names', 'resolve_url', 'responses', 'reverse_lookup', 'save_delete_hooks', 'schema', 'select_for_update', 'select_related', 'select_related_onetoone', 'select_related_regress', 'serializers', 'servers', 'sessions_tests', 'settings_tests', 'shell', 'shortcuts', 'signals', 'signed_cookies_tests', 'signing', 'sitemaps_tests', 'sites_framework', 'sites_tests', 'staticfiles_tests', 'str', 'string_lookup', 'swappable_models', 'syndication_tests', 'template_backends', 'template_loader', 'template_tests', 'templates', 'test_client', 'test_client_regress', 'test_exceptions', 'test_runner', 'test_runner_apps', 'test_utils', 'timezones', 'transaction_hooks', 'transactions', 'unmanaged_models', 'update', 'update_only_fields', 'urlpatterns', 'urlpatterns_reverse', 'user_commands', 'utils_tests', 'validation', 'validators', 'version', 'view_tests', 'wsgi'
]

if __name__ == '__main__':
    i = int(sys.argv[len(sys.argv)-1])
    f = sys.argv[0].split('/')[:-1]
    f.append('runtests.py')
    sys.argv[0] = '/'.join(f)
    t_i = len(sys.argv) - 1

    while i < len(tests):
        sys.argv[t_i] = tests[i]
        print(f'## Executing test: {tests[i]} no: {i} ##\n')
        execfile('runtests.py')
        print(f'## Ran test: {tests[i]} no: {i} ##\n')
        i += 1
