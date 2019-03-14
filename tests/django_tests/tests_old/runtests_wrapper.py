import subprocess
import sys
import logging
import argparse
from runtests import parser

djongo_logger = logging.getLogger('djongo')
djongo_logger.setLevel(logging.INFO)

tests = ['admin_registration', 'timezones', 'model_meta', 'null_fk', 'm2m_regress', 'settings_tests', 'model_package', 'model_formsets', 'nested_foreign_keys', 'test_client_regress', 'defer_regress', 'test_utils', 'get_or_create', 'save_delete_hooks', 'm2m_multiple', 'extra_regress', 'admin_custom_urls', 'reserved_names', 'many_to_many', 'test_exceptions', 'signals', 'migrations2', 'select_related_regress', 'm2m_recursive', 'deprecation', 'select_related', 'test_runner_apps', 'empty', 'app_loading', 'decorators', 'shell', 'proxy_model_inheritance', 'file_storage', 'update_only_fields', 'custom_pk', 'aggregation', 'apps', 'known_related_objects', 'contenttypes_tests', 'delete_regress', 'mutually_referential', 'from_db_value', 'get_earliest_or_latest', 'model_formsets_regress', 'conditional_processing', 'order_with_respect_to', 'filtered_relation', 'model_options', 'resolve_url', 'm2m_and_m2o', 'string_lookup', 'servers', 'ordering', 'no_models', 'm2o_recursive', 'foreign_object', 'db_utils', 'file_uploads', 'project_template', 'migrate_signals', 'admin_ordering', 'inline_formsets', 'unmanaged_models', 'httpwrappers', 'dbshell', 'indexes', 'str', 'm2m_through_regress', 'wsgi', 'max_lengths', 'sites_tests', 'fixtures_model_package', 'absolute_url_overrides', 'base', 'm2m_signals', 'custom_methods', 'field_subclassing', 'defer', 'redirects_tests', 'admin_autodiscover', 'expressions_window', 'reverse_lookup', 'template_loader', 'or_lookups', 'choices', 'null_queries', 'pagination', 'update', 'raw_query', 'select_for_update', 'model_inheritance_regress', 'admin_docs', 'signing', 'm2m_intermediary', 'fixtures', 'introspection', 'field_defaults', 'syndication_tests', 'fixtures_regress', 'urlpatterns', 'shortcuts', 'null_fk_ordering', 'swappable_models', 'sitemaps_tests', 'signed_cookies_tests', 'requirements', 'humanize_tests', 'sites_framework', 'model_regress', 'middleware', 'aggregation_regress', 'distinct_on_fields', 'db_typecasts', 'check_framework', 'handlers', 'middleware_exceptions', 'dispatch', 'flatpages_tests', 'custom_migration_operations', 'context_processors', 'delete', 'transactions', 'version', 'generic_inline_admin', 'bash_completion', 'templates', 'force_insert_update', 'm2m_through', 'migration_test_data_persistence', 'properties', 'admin_checks', 'custom_columns', 'transaction_hooks', 'many_to_one_null', 'builtin_server']


failed_tests = []
wrapper_parser = argparse.ArgumentParser(parents=[parser], add_help=False)

wrapper_parser.add_argument('--startindex', default=None, type=int)
wrapper_parser.add_argument('--runall', action='store_true', dest='runall')

if __name__ == '__main__':
    parsed = wrapper_parser.parse_args()
    # start_index = int(sys.argv[len(sys.argv) - 1])
    f = sys.argv[0].split('/')[:-1]
    f.append('runtests.py')
    sys.argv[0] = '/'.join(f)

    for arg in sys.argv:
        if arg.startswith('--startindex'):
            sys.argv.remove(arg)
            break

    if parsed.startindex is None:
        # Run all tests
        o = subprocess.run((['python'] + sys.argv))
    else:
        start_index = parsed.startindex
        # argv_test_i = len(sys.argv) - 1

        for i, test in enumerate(tests[start_index:]):
            index = i + start_index
            sys.argv.append(test)
            print(f'## Executing test: {test} no: {index} ##\n')
            o = subprocess.run((['python'] + sys.argv))
            if o.returncode != 0:
                failed_tests.append(test)
            print(f'## Ran test: {test} no: {index} ##\n')
        # while start_index < len(tests):
    #     sys.argv[t_i] = tests[start_index]
    #     print(f'## Executing test: {tests[start_index]} no: {i} ##\n')
    #     o = subprocess.run((['python'] + sys.argv))
    #     if o.returncode != 0:
    #         failed_tests.append(tests[start_index])
    #     print(f'## Ran test: {tests[start_index]} no: {i} ##\n')
    #     start_index += 1
        print('failed tests \n', failed_tests)

#Fail 1:
# ['null_fk', 'm2m_regress', 'model_package', 'model_formsets', 'nested_foreign_keys', 'test_client_regress', 'defer_regress', 'test_utils', 'get_or_create', 'extra_regress', 'admin_custom_urls', 'reserved_names', 'many_to_many', 'signals', 'select_related_regress', 'select_related', 'empty', 'proxy_model_inheritance', 'update_only_fields', 'custom_pk', 'aggregation', 'known_related_objects', 'contenttypes_tests', 'delete_regress', 'from_db_value', 'get_earliest_or_latest', 'model_formsets_regress', 'order_with_respect_to', 'filtered_relation', 'm2m_and_m2o', 'servers', 'ordering', 'foreign_object', 'admin_ordering', 'unmanaged_models', 'm2m_through_regress', 'sites_tests', 'custom_methods', 'defer', 'redirects_tests', 'reverse_lookup', 'or_lookups', 'null_queries', 'pagination', 'update', 'raw_query', 'select_for_update', 'model_inheritance_regress', 'admin_docs', 'm2m_intermediary', 'fixtures', 'introspection', 'syndication_tests', 'fixtures_regress', 'sitemaps_tests', 'sites_framework', 'model_regress', 'aggregation_regress', 'flatpages_tests', 'delete', 'transactions', 'generic_inline_admin', 'force_insert_update', 'm2m_through', 'custom_columns', 'transaction_hooks', 'many_to_one_null']

#Fail 2:

# ['timezones', 'null_fk', 'm2m_regress', 'model_formsets', 'nested_foreign_keys', 'test_client_regress', 'defer_regress', 'test_utils', 'get_or_create', 'extra_regress', 'admin_custom_urls', 'reserved_names', 'many_to_many', 'signals', 'select_related_regress', 'select_related', 'empty', 'proxy_model_inheritance', 'update_only_fields', 'custom_pk', 'aggregation', 'known_related_objects', 'contenttypes_tests', 'delete_regress', 'from_db_value', 'get_earliest_or_latest', 'model_formsets_regress', 'order_with_respect_to', 'filtered_relation', 'm2m_and_m2o', 'servers', 'ordering', 'foreign_object', 'admin_ordering', 'unmanaged_models', 'm2m_through_regress', 'sites_tests', 'custom_methods', 'defer', 'redirects_tests', 'reverse_lookup', 'or_lookups', 'null_queries', 'pagination', 'update', 'raw_query', 'select_for_update', 'model_inheritance_regress', 'admin_docs', 'm2m_intermediary', 'fixtures', 'introspection', 'syndication_tests', 'fixtures_regress', 'sitemaps_tests', 'sites_framework', 'model_regress', 'aggregation_regress', 'flatpages_tests', 'delete', 'transactions', 'generic_inline_admin', 'bash_completion', 'templates', 'force_insert_update', 'm2m_through', 'migration_test_data_persistence', 'properties', 'admin_checks', 'custom_columns', 'transaction_hooks', 'many_to_one_null', 'builtin_server']

#Fail 3 Mongo:
 # ['timezones', 'model_formsets', 'nested_foreign_keys', 'test_client_regress', 'defer_regress', 'test_utils', 'get_or_create', 'extra_regress', 'admin_custom_urls', 'reserved_names', 'many_to_many', 'signals', 'select_related_regress', 'select_related', 'update_only_fields', 'custom_pk', 'aggregation', 'contenttypes_tests', 'delete_regress', 'from_db_value', 'get_earliest_or_latest', 'model_formsets_regress', 'order_with_respect_to', 'filtered_relation', 'servers', 'ordering', 'foreign_object', 'admin_ordering', 'm2m_through_regress', 'sites_tests', 'custom_methods', 'defer', 'redirects_tests', 'reverse_lookup', 'or_lookups', 'null_queries', 'pagination', 'update', 'raw_query', 'select_for_update', 'model_inheritance_regress', 'admin_docs', 'm2m_intermediary', 'fixtures', 'introspection', 'syndication_tests', 'fixtures_regress', 'sitemaps_tests', 'sites_framework', 'model_regress', 'aggregation_regress', 'flatpages_tests', 'delete', 'transactions', 'generic_inline_admin', 'force_insert_update', 'm2m_through', 'custom_columns', 'transaction_hooks', 'many_to_one_null']
 
 #Fail 4:
 # ['timezones', 'model_formsets', 'test_utils', 'get_or_create', 'extra_regress', 'reserved_names', 'many_to_many', 'select_related_regress', 'select_related', 'custom_pk', 'aggregation', 'contenttypes_tests', 'delete_regress', 'get_earliest_or_latest', 'order_with_respect_to', 'filtered_relation', 'ordering', 'foreign_object', 'admin_ordering', 'm2m_through_regress', 'custom_methods', 'defer', 'or_lookups', 'null_queries', 'update', 'raw_query', 'model_inheritance_regress', 'fixtures', 'introspection', 'syndication_tests', 'fixtures_regress', 'sitemaps_tests', 'model_regress', 'aggregation_regress', 'delete', 'transactions', 'force_insert_update', 'transaction_hooks']