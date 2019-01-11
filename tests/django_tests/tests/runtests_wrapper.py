import subprocess
import sys
import logging
import argparse
from runtests import parser

djongo_logger = logging.getLogger('djongo')
djongo_logger.setLevel(logging.INFO)

all_tests = ['absolute_url_overrides', 'admin_autodiscover', 'admin_changelist', 'admin_checks', 'admin_custom_urls', 'admin_default_site', 'admin_docs', 'admin_filters', 'admin_inlines', 'admin_ordering', 'admin_registration', 'admin_scripts', 'admin_utils', 'admin_views', 'admin_widgets', 'aggregation', 'aggregation_regress', 'annotations', 'app_loading', 'apps', 'auth_tests', 'backends', 'base', 'bash_completion', 'basic', 'builtin_server', 'bulk_create', 'cache', 'check_framework', 'choices', 'conditional_processing', 'contenttypes_tests', 'context_processors', 'csrf_tests', 'custom_columns', 'custom_lookups', 'custom_managers', 'custom_methods', 'custom_migration_operations', 'custom_pk', 'datatypes', 'dates', 'datetimes', 'db_functions', 'db_typecasts', 'db_utils', 'dbshell', 'decorators', 'defer', 'defer_regress', 'delete', 'delete_regress', 'deprecation', 'dispatch', 'distinct_on_fields', 'empty', 'expressions', 'expressions_case', 'expressions_window', 'extra_regress', 'field_deconstruction', 'field_defaults', 'field_subclassing', 'file_storage', 'file_uploads', 'files', 'filtered_relation', 'fixtures', 'fixtures_model_package', 'fixtures_regress', 'flatpages_tests', 'force_insert_update', 'foreign_object', 'forms_tests', 'from_db_value', 'generic_inline_admin', 'generic_relations', 'generic_relations_regress', 'generic_views', 'get_earliest_or_latest', 'get_object_or_404', 'get_or_create', 'gis_tests', 'handlers', 'httpwrappers', 'humanize_tests', 'i18n', 'import_error_package', 'indexes', 'inline_formsets', 'inspectdb', 'introspection', 'invalid_models_tests', 'known_related_objects', 'logging_tests', 'lookup', 'm2m_and_m2o', 'm2m_intermediary', 'm2m_multiple', 'm2m_recursive', 'm2m_regress', 'm2m_signals', 'm2m_through', 'm2m_through_regress', 'm2o_recursive', 'mail', 'managers_regress', 'many_to_many', 'many_to_one', 'many_to_one_null', 'max_lengths', 'messages_tests', 'middleware', 'middleware_exceptions', 'migrate_signals', 'migration_test_data_persistence', 'migrations', 'migrations2', 'model_fields', 'model_forms', 'model_formsets', 'model_formsets_regress', 'model_indexes', 'model_inheritance', 'model_inheritance_regress', 'model_meta', 'model_options', 'model_package', 'model_regress', 'modeladmin', 'multiple_database', 'mutually_referential', 'nested_foreign_keys', 'no_models', 'null_fk', 'null_fk_ordering', 'null_queries', 'one_to_one', 'or_lookups', 'order_with_respect_to', 'ordering', 'pagination', 'postgres_tests', 'prefetch_related', 'project_template', 'properties', 'proxy_model_inheritance', 'proxy_models', 'queries', 'queryset_pickle', 'raw_query', 'redirects_tests', 'requests', 'requirements', 'reserved_names', 'resolve_url', 'responses', 'reverse_lookup', 'save_delete_hooks', 'schema', 'select_for_update', 'select_related', 'select_related_onetoone', 'select_related_regress', 'serializers', 'servers', 'sessions_tests', 'settings_tests', 'shell', 'shortcuts', 'signals', 'signed_cookies_tests', 'signing', 'sitemaps_tests', 'sites_framework', 'sites_tests', 'staticfiles_tests', 'str', 'string_lookup', 'swappable_models', 'syndication_tests', 'template_backends', 'template_loader', 'template_tests', 'templates', 'test_client', 'test_client_regress', 'test_exceptions', 'test_runner', 'test_runner_apps', 'test_utils', 'timezones', 'transaction_hooks', 'transactions', 'unmanaged_models', 'update', 'update_only_fields', 'urlpatterns', 'urlpatterns_reverse', 'user_commands', 'utils_tests', 'validation', 'validators', 'version', 'view_tests']

failing_tests = ['admin_changelist', 'admin_checks', 'admin_filters', 'admin_ordering', 'admin_utils', 'admin_views', 'aggregation', 'aggregation_regress', 'annotations', 'auth_tests', 'backends', 'basic', 'bulk_create', 'cache', 'contenttypes_tests', 'custom_columns', 'custom_lookups', 'custom_managers', 'custom_methods', 'custom_pk', 'datatypes', 'dates', 'datetimes', 'db_functions', 'defer', 'delete', 'delete_regress', 'expressions', 'expressions_case', 'extra_regress', 'filtered_relation', 'fixtures', 'fixtures_regress', 'force_insert_update', 'foreign_object', 'generic_relations', 'generic_relations_regress', 'generic_views', 'get_earliest_or_latest', 'get_or_create', 'gis_tests', 'import_error_package', 'inspectdb', 'introspection', 'lookup', 'm2m_through_regress', 'many_to_many', 'many_to_one', 'migrations', 'model_fields', 'model_forms', 'model_formsets', 'model_inheritance', 'model_inheritance_regress', 'model_regress', 'modeladmin', 'multiple_database', 'null_queries', 'one_to_one', 'or_lookups', 'order_with_respect_to', 'ordering', 'prefetch_related', 'proxy_models', 'queries', 'queryset_pickle', 'raw_query', 'reserved_names', 'schema', 'select_related', 'select_related_onetoone', 'select_related_regress', 'serializers', 'sitemaps_tests', 'syndication_tests', 'test_runner', 'test_utils', 'timezones', 'transaction_hooks', 'transactions', 'update', 'validation', 'view_tests']

failed_tests = []
wrapper_parser = argparse.ArgumentParser(parents=[parser], add_help=False)

wrapper_parser.add_argument('--startindex', default=None, type=int)
wrapper_parser.add_argument('--currentlypassing', action='store_true', dest='currentlypassing')

if __name__ == '__main__':
    parsed = wrapper_parser.parse_args()
    # start_index = int(sys.argv[len(sys.argv) - 1])
    f = sys.argv[0].split('/')[:-1]
    f.append('runtests.py')
    sys.argv[0] = '/'.join(f)
    exit_code = 0

    for arg in sys.argv:
        if(arg.startswith('--startindex')
                or arg.startswith('--currentlypassing')):
            sys.argv.remove(arg)

    if parsed.currentlypassing:
        currently_failing = []
        passing = set(all_tests) - set(failing_tests)
        sys.argv.append('dummy_test')
        for tst in passing:
            sys.argv[-1] = tst
            print(f'## Executing test: {tst} ##\n')
            o = subprocess.run((['python'] + sys.argv))
            if o.returncode != 0:
                currently_failing.append(tst)
                exit_code = 1
            print(f'## Ran test: {tst}##\n')

        print('failed tests \n', currently_failing)

    elif parsed.startindex is None:
        # Run all tests
        o = subprocess.run((['python'] + sys.argv))
    else:
        start_index = parsed.startindex
        # argv_test_i = len(sys.argv) - 1
        sys.argv.append('dummy_test')
        for i, test in enumerate(all_tests[start_index:]):
            index = i + start_index
            sys.argv[-1] = test
            print(f'## Executing test: {test} no: {index} ##\n')
            o = subprocess.run((['python'] + sys.argv))
            if o.returncode != 0:
                failed_tests.append(test)
                exit_code = 1
            print(f'## Ran test: {test} no: {index} ##\n')
        print('failed tests \n', failed_tests)

    exit(exit_code)
