import os
import re
import sys

TEST_DIR = os.path.dirname(os.path.realpath(__file__))
LOG_DIR = os.path.join(TEST_DIR, 'logs')


def parse(log_file, sql_file):
    found_sqls = set()
    marker = 'sql_command: '
    with open(log_file, 'r') as log, open(sql_file, 'w') as sql_fd:
        for line in log:
            if line.startswith(marker):
                sql = line[len(marker):]
                sql = normalize_sql_easy(sql)
                found_sqls.add(sql)

        found_sqls = sorted(found_sqls)
        sql_fd.writelines(found_sqls)


def normalize_sql(sql):
    index = sql.find('"')
    normalized_sql = ''
    while index != -1:
        normalized_sql = ''.join((normalized_sql, sql[:index], '"some_name"'))
        sql = sql[index+1:]
        index = sql.find('"')
        sql = sql[index+1:]
        index = sql.find('"')

    normalized_sql += sql
    return normalized_sql


def normalize_sql_easy(sql):
    return re.sub(r'".+?"', '"some_name"', sql)


if __name__ == '__main__':
    inp = os.path.join(LOG_DIR, 'django_v22_mongodb_1.txt')
    out = os.path.join(LOG_DIR, 'sqls_mongodb_1.txt')
    parse(inp, out)
