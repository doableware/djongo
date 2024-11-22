"""
Module with constants and mappings to build MongoDB queries from
SQL constructors.
"""
import itertools
import re
from logging import getLogger
from typing import Optional, Dict, List, Union as U, Sequence, Set
from dataclasses import dataclass, field as dataclass_field
from pymongo import MongoClient
from pymongo import ReturnDocument
from pymongo.command_cursor import CommandCursor
from pymongo.cursor import Cursor as BasicCursor
from pymongo.database import Database
from pymongo.errors import OperationFailure, CollectionInvalid
from sqlparse import parse as sqlparse
from sqlparse import tokens
from sqlparse.sql import (
    Identifier,
    Parenthesis,
    Where,
    Values,
    Statement
)

from ..exceptions import SQLDecodeError, MigrationError, print_warn
from .functions import SQLFunc
from .sql_tokens import (SQLToken, SQLStatement, SQLIdentifier,
                         AliasableToken, SQLConstIdentifier, SQLColumnDef, SQLColumnConstraint)
from .converters import (
    ColumnSelectConverter,
    AggColumnSelectConverter,
    FromConverter,
    VoidConverter,
    VoidSelectConverter,
    WhereConverter,
    AggWhereConverter,
    InnerJoinConverter,
    OuterJoinConverter,
    LimitConverter,
    AggLimitConverter,
    OrderConverter,
    SetConverter,
    AggOrderConverter,
    DistinctConverter,
    NestedInQueryConverter,
    GroupbyConverter,
    OffsetConverter,
    AggOffsetConverter,
    HavingConverter
)

from djongo import base
logger = getLogger(__name__)


@dataclass
class TokenAlias:
    alias2token: Dict[str, U[AliasableToken,
                             SQLFunc,
                             SQLIdentifier]] = dataclass_field(default_factory=dict)
    token2alias: Dict[U[AliasableToken,
                        SQLFunc,
                        SQLIdentifier], str] = dataclass_field(default_factory=dict)
    aliased_names: Set[str] = dataclass_field(default_factory=set)


class Query:
    func_interface: str
    count_interface: str

    def __init__(self,
                 client_connection: MongoClient,
                 db: Database,
                 connection_properties: 'base.DjongoClient',
                 statement: Statement,
                 params: Sequence):
        self.statement = statement
        self.db = db
        self.cli_con = client_connection
        self.connection_properties = connection_properties
        self.params = params
        self.token_alias = TokenAlias()
        self.nested_query: Optional[NestedInQueryConverter] = None
        self.left_table: Optional[str] = None
        self._cursor = None
        self.parse()

    def __iter__(self):
        raise NotImplementedError

    def __next__(self):
        raise NotImplementedError

    def parse(self):
        raise NotImplementedError

    def count(self):
        raise NotImplementedError

    def close(self):
        return

    @staticmethod
    def execute(client_connection: MongoClient,
                db_connection: Database,
                connection_properties: 'base.DjongoClient',
                sql: str,
                params: Optional[Sequence]):
        import djongo
        exe = SQLDecodeError(
            err_sql=sql,
            params=params,
            version=djongo.__version__
        )
        logger.debug(
            f'sql_command: {sql}\n'
            f'params: {params}'
        )
        count = itertools.count()
        sql = re.sub(r'%s', lambda _: f'%({next(count)})s', sql)
        statement = sqlparse(sql)

        if len(statement) > 1:
            raise exe

        statement = statement[0]
        sm_type = statement.get_type()

        try:
            query = Query.FUNC_MAP[sm_type](client_connection,
                                        db_connection,
                                        connection_properties,
                                        statement,
                                        params)
        except KeyError:
            logger.debug(f'Not implemented "{sm_type}" of "{statement}"')
            raise exe

        except MigrationError:
            raise

        except SQLDecodeError as e:
            e.err_sql = sql,
            e.params = params,
            e.version = djongo.__version__
            raise e

        except Exception as e:
            raise exe from e

        return query

    def _execute(self):
        raise NotImplementedError

class DDLQuery(Query):


    def __init__(self, *args):
        super().__init__(*args)
        self._execute()

    def __iter__(self):
        return

    def __next__(self):
        raise StopIteration

DMLQuery = DDLQuery

class DQLQuery(Query):

    def _execute(self):
        raise TypeError(f'DQL Query execute on __iter__')

    def count(self):
        raise NotImplementedError

class SelectQueryStage(dict):
    agg_cast = {
        WhereConverter: AggWhereConverter,
        OrderConverter: AggOrderConverter,
        OffsetConverter: AggOffsetConverter,
        LimitConverter: AggLimitConverter,
        ColumnSelectConverter: AggColumnSelectConverter
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.needs_aggregation = False
        self.needs_column_selection = True


    def values(self):
        if not self.needs_column_selection:
            self['SELECT'].__class__ = VoidSelectConverter

        for stage in super().values():
            if not isinstance(stage, type | VoidConverter):
                if self.needs_aggregation:
                    try:
                        stage.__class__ = self.agg_cast[type(stage)]
                    except KeyError:
                        pass
                yield stage


class SelectQueryStageGet:

    def __init__(self, name:str=None):
        self.name = name

    def __set_name__(self, owner, name: str):
        if not self.name:
            self.name = name

    def __get__(self, instance: 'SelectQuery', owner):
        ret = instance.stages[self.name.upper()]
        if not isinstance(ret, type):
            return ret
        return None

class SelectQuery(DQLQuery):

    def __init__(self, *args):

        self._cursor: Optional[U[BasicCursor, CommandCursor]] = None
        self._result_generator = None
        self.stages = SelectQueryStage(**{
            'INNER JOIN': InnerJoinConverter,
            'LEFT OUTER JOIN': OuterJoinConverter,
            'nested_query': NestedInQueryConverter,
            'WHERE': WhereConverter,
            'GROUP BY': GroupbyConverter,
            'HAVING': HavingConverter,
            'DISTINCT': DistinctConverter,
            'ORDER BY': OrderConverter,
            'OFFSET': OffsetConverter,
            'LIMIT': LimitConverter,
            'SELECT': ColumnSelectConverter,
            'FROM': FromConverter,
        })
        super().__init__(*args)

    distinct = SelectQueryStageGet()
    selected_columns = SelectQueryStageGet('SELECT')


    def parse(self):
        statement = SQLStatement(self.statement)

        for tok in statement:
            try:
                self.stages[str(tok)] = self.stages[str(tok)](self, statement)
            except KeyError:
                if isinstance(tok, Where):
                    self.stages['WHERE'] = self.stages['WHERE'](self, statement)
                else:
                    raise SQLDecodeError(f'Unknown keyword: {tok}')

    def __iter__(self):
        try:
            yield from self._iter()

        except MigrationError:
            raise

        except Exception as e:
            import djongo
            exe = SQLDecodeError(
                err_sql=self.statement,
                params=self.params,
                version=djongo.__version__
            )
            raise exe from e

    def _iter(self):
        if self._cursor is None:
            self._cursor = self._get_cursor()

        cursor = self._cursor
        if not cursor.alive:
            return

        for doc in cursor:
            yield self._align_results(doc)
        return

    def __next__(self):
        if self._result_generator is None:
            self._result_generator = iter(self)

        result = next(self._result_generator)
        logger.debug(f'Result: {result}')
        return result

    def close(self):
        if self._cursor:
            self._cursor.close()

    def count(self):

        if self._cursor is None:
            self._cursor = self._get_cursor()
        return len(list(self._cursor))

    def _check_aggregation(self):
        if any(isinstance(sql_token, (SQLFunc, SQLConstIdentifier))
               for sql_token in self.selected_columns.sql_tokens):
            self.stages.needs_aggregation = True


    def _make_pipeline(self):
        pipeline = []
        for stage in self.stages.values():
            doc = stage.to_mongo()
            if isinstance(doc, dict):
                pipeline.append(doc)
            else:
                pipeline.extend(doc)

        return pipeline


    def _get_cursor(self):
        self._check_aggregation()
        if self.stages.needs_aggregation:
            pipeline = self._make_pipeline()
            cur = self.db[self.left_table].aggregate(pipeline)
            logger.debug(f'Aggregation query: {pipeline}')
        else:
            kwargs = {}
            for stage in self.stages.values():
                kwargs.update(stage.to_mongo())

            cur = self.db[self.left_table].find(**kwargs)
            logger.debug(f'Find query: {kwargs}')

        return cur

    def _align_results(self, doc):
        ret = []
        if self.distinct:
            sql_tokens = self.distinct.sql_tokens
        else:
            sql_tokens = self.selected_columns.sql_tokens

        for selected in sql_tokens:
            if isinstance(selected, SQLIdentifier):
                if selected.table == self.left_table:
                    try:
                        ret.append(doc[selected.column])
                    except KeyError:
                        if self.connection_properties.enforce_schema:
                            raise MigrationError(selected.column)
                        ret.append(None)
                else:
                    try:
                        ret.append(doc[selected.table][selected.column])
                    except KeyError:
                        if self.connection_properties.enforce_schema:
                            raise MigrationError(selected.column)
                        ret.append(None)
            else:
                ret.append(doc[selected.alias])

        return tuple(ret)


class UpdateQuery(DMLQuery):

    def __init__(self, *args):
        self.selected_table: Optional[ColumnSelectConverter] = None
        self.set_columns: Optional[SetConverter] = None
        self.where: Optional[WhereConverter] = None
        self.result = None
        self.kwargs = None
        super().__init__(*args)

    def count(self):
        return self.result.matched_count

    def parse(self):

        statement = SQLStatement(self.statement)

        for tok in statement:
            if tok.match(tokens.DML, 'UPDATE'):
                c = ColumnSelectConverter(self, statement)
                self.left_table = c.sql_tokens[0].table

            elif tok.match(tokens.Keyword, 'SET'):
                c = self.set_columns = SetConverter(self, statement)

            elif isinstance(tok, Where):
                c = self.where = WhereConverter(self, statement)

            else:
                raise SQLDecodeError

        self.kwargs = {}
        if self.where:
            self.kwargs.update(self.where.to_mongo())

        self.kwargs.update(self.set_columns.to_mongo())

    def _execute(self):
        db = self.db
        self.result = db[self.left_table].update_many(**self.kwargs)
        logger.debug(f'update_many: {self.result.modified_count}, matched: {self.result.matched_count}')


class InsertQuery(DMLQuery):

    def __init__(self,
                 *args):
        self.last_row_id = 0
        self._cols = None
        self._values = []
        super().__init__(*args)

    def _table(self, statement: SQLStatement):
        tok = statement.next()
        collection = tok.get_name()
        if collection not in self.connection_properties.cached_collections:
            if self.connection_properties.enforce_schema:
                raise MigrationError(f'Table {collection} does not exist in database')
            self.connection_properties.cached_collections.add(collection)

        self.left_table = collection

    def _columns(self, statement: SQLStatement):
        tok = statement.next()
        self._cols = [token.column for token in SQLToken.tokens2sql(tok[1], self)]

    def _fill_values(self, statement: SQLStatement):
        tok_value = statement.next()
        if not isinstance(tok_value, Values):
            raise SQLDecodeError
        for tok in tok_value:
            if isinstance(tok, Parenthesis):
                placeholder = SQLToken.token2sql(tok, self)
                values = []
                for index in placeholder:
                    if isinstance(index, int):
                        values.append(self.params[index])
                    else:
                        values.append(index)
                self._values.append(values)

    def _execute(self):
        docs = []
        num = len(self._values)

        auto = self.db['__schema__'].find_one_and_update(
            {
                'name': self.left_table,
                'auto': {
                    '$exists': True
                }
            },
            {'$inc': {'auto.seq': num}},
            return_document=ReturnDocument.AFTER
        )

        for i, val in enumerate(self._values):
            ins = {}
            if auto:
                for name in auto['auto']['field_names']:
                    ins[name] = int(auto['auto']['seq']) - num + i + 1
            for _field, value in zip(self._cols, val):
                if (auto and _field in auto['auto']['field_names']
                        and value == 'DEFAULT'):
                    continue
                ins[_field] = value
            docs.append(ins)

        res = self.db[self.left_table].insert_many(docs, ordered=False)
        if auto:
            self.last_row_id = int(auto['auto']['seq'])
        else:
            self.last_row_id = res.inserted_ids[-1]
        logger.debug('inserted ids {}'.format(res.inserted_ids))

    def parse(self):
        statement = SQLStatement(self.statement)
        # Skip to table name
        statement.skip(4)
        self._table(statement)
        self._columns(statement)
        self._fill_values(statement)


class AlterQuery(DDLQuery):

    def __init__(self, *args):
        self._iden_name = None
        self._old_name = None
        self._new_name = None
        self._default = None
        self._type_code = None
        self._cascade = None
        self._null = None

        super().__init__(*args)

    def parse(self):
        statement = SQLStatement(self.statement)
        statement.skip(2)

        for tok in statement:
            if tok.match(tokens.Keyword, 'TABLE'):
                self._table(statement)
            elif tok.match(tokens.Keyword, 'ADD'):
                self._add(statement)
            elif tok.match(tokens.Keyword, 'FLUSH'):
                self._execute = self._flush
            elif tok.match(tokens.Keyword.DDL, 'DROP'):
                self._drop(statement)
            elif tok.match(tokens.Keyword.DDL, 'ALTER'):
                self._alter(statement)
            elif tok.match(tokens.Keyword, 'RENAME'):
                self._rename(statement)
            else:
                raise SQLDecodeError(f'Unknown token {tok}')

    def _rename(self, statement: SQLStatement):
        column = False
        to = False
        for tok in statement:
            if tok.match(tokens.Keyword, 'COLUMN'):
                self._execute = self._rename_column
                column = True
            if tok.match(tokens.Keyword, 'TO'):
                to = True
            elif isinstance(tok, Identifier):
                if not to:
                    self._old_name = tok.get_real_name()
                else:
                    self._new_name = tok.get_real_name()

        if not column:
            # Rename table
            self._execute = self._rename_collection

    def _rename_column(self):
        self.db[self.left_table].update_many(
            {},
            {
                '$rename': {
                    self._old_name: self._new_name
                }
            },
        )

    def _rename_collection(self):
        self.db[self.left_table].rename(self._new_name)

    def _alter(self, statement: SQLStatement):
        self._execute = lambda: None
        feature = ''

        for tok in statement:
            if isinstance(tok, Identifier):
                pass
            elif tok.ttype == tokens.Name.Placeholder:
                pass
            elif tok.match(tokens.Keyword, (
                    'NOT NULL', 'NULL', 'COLUMN',
            )):
                feature += str(tok) + ' '
            elif tok.match(tokens.Keyword.DDL, 'DROP'):
                feature += 'DROP '
            elif tok.match(tokens.Keyword, 'DEFAULT'):
                feature += 'DEFAULT '
            elif tok.match(tokens.Keyword, 'SET'):
                feature += 'SET '
            else:
                raise SQLDecodeError(f'Unknown token: {tok}')

        print_warn(feature)

    def _flush(self):
        self.db[self.left_table].delete_many({})

    def _table(self, statement: SQLStatement):
        tok = statement.next()
        if not tok:
            raise SQLDecodeError
        self.left_table = SQLToken.token2sql(tok, self).table

    def _drop(self, statement: SQLStatement):

        for tok in statement:
            if tok.match(tokens.Keyword, 'CASCADE'):
                print_warn('DROP CASCADE')
            elif isinstance(tok, Identifier):
                self._iden_name = tok.get_real_name()
            elif tok.match(tokens.Keyword, 'INDEX'):
                self._execute = self._drop_index
            elif tok.match(tokens.Keyword, 'CONSTRAINT'):
                pass
            elif tok.match(tokens.Keyword, 'COLUMN'):
                self._execute = self._drop_column
            else:
                raise SQLDecodeError

    def _drop_index(self):
        self.db[self.left_table].drop_index(self._iden_name)

    def _drop_column(self):
        self.db[self.left_table].update_many(
            {},
            {
                '$unset': {
                    self._iden_name: ''
                }
            },
        )
        self.db['__schema__'].update_one(
            {'name': self.left_table},
            {
                '$unset': {
                    f'fields.{self._iden_name}': ''
                }
            }
        )

    def _add(self, statement: SQLStatement):
        for tok in statement:
            if tok.match(tokens.Keyword, (
                'CONSTRAINT', 'KEY', 'REFERENCES',
                'NOT NULL', 'NULL'
            )):
                print_warn(f'schema validation using {tok}')

            elif tok.match(tokens.Name.Builtin, '.*', regex=True):
                print_warn('column type validation')
                self._type_code = str(tok)

            elif tok.match(tokens.Keyword, 'double'):
                print_warn('column type validation')
                self._type_code = str(tok)

            elif isinstance(tok, Identifier):
                self._iden_name = tok.get_real_name()

            elif isinstance(tok, Parenthesis):
                self.field_dir = [
                    (field.strip(' "'), 1)
                    for field in tok.value.strip('()').split(',')
                ]

            elif tok.match(tokens.Keyword, 'DEFAULT'):
                tok = statement.next()
                i = SQLToken.placeholder_index(tok)
                self._default = self.params[i]

            elif tok.match(tokens.Keyword, 'UNIQUE'):
                if self._execute == self._add_column:
                    self.field_dir = [(self._iden_name, 1)]
                self._execute = self._unique

            elif tok.match(tokens.Keyword, 'INDEX'):
                self._execute = self._index

            elif tok.match(tokens.Keyword, 'FOREIGN'):
                self._execute = self._fk

            elif tok.match(tokens.Keyword, 'COLUMN'):
                self._execute = self._add_column

            elif isinstance(tok, Where):
                print_warn('partial indexes')

            else:
                raise SQLDecodeError(err_key=tok.value,
                                     err_sub_sql=statement)

    def _add_column(self):
        self.db[self.left_table].update_many(
            {
                '$or': [
                    {self._iden_name: {'$exists': False}},
                    {self._iden_name: None}
                ]
            },
            {
                '$set': {
                    self._iden_name: self._default
                }
            },
        )
        self.db['__schema__'].update_one(
            {'name': self.left_table},
            {
                '$set': {
                    f'fields.{self._iden_name}': {
                        'type_code': self._type_code
                    }
                }
            }
        )

    def _index(self):
        self.db[self.left_table].create_index(
            self.field_dir,
            name=self._iden_name)

    def _unique(self):
        self.db[self.left_table].create_index(
            self.field_dir,
            unique=True,
            name=self._iden_name)

    def _fk(self):
        pass



class CreateQuery(DDLQuery):

    def __init__(self, *args):
        super().__init__(*args)

    def _execute(self):
        return

    def _create_table(self, statement):
        if '__schema__' not in self.connection_properties.cached_collections:
            self.db.create_collection('__schema__')
            self.connection_properties.cached_collections.add('__schema__')
            self.db['__schema__'].create_index('name', unique=True)
            self.db['__schema__'].create_index('auto')

        tok = statement.next()
        table = SQLToken.token2sql(tok, self).table
        try:
            self.db.create_collection(table)
        except CollectionInvalid:
            if self.connection_properties.enforce_schema:
                raise
            else:
                return

        logger.debug('Created table: {}'.format(table))

        tok = statement.next()
        if not isinstance(tok, Parenthesis):
            raise SQLDecodeError(f'Unexpected sql syntax'
                                 f' for column definition: {statement}')

        if statement.next():
            raise SQLDecodeError(f'Unexpected sql syntax'
                                 f' for column definition: {statement}')

        _filter = {
            'name': table
        }
        _set = {}
        push = {}
        update = {}

        for col in SQLColumnDef.sql2col_defs(tok.value):
            if isinstance(col, SQLColumnConstraint):
                print_warn('column CONSTRAINTS')
            else:
                field = col.name
                if field == '_id':
                    continue

                _set[f'fields.{field}'] = {
                    'type_code': col.data_type
                }

                if SQLColumnDef.autoincrement in col.col_constraints:
                    try:
                        push['auto.field_names']['$each'].append(field)
                    except KeyError:
                        push['auto.field_names'] = {
                            '$each': [field]
                        }
                    _set['auto.seq'] = 0

                if SQLColumnDef.primarykey in col.col_constraints:
                    self.db[table].create_index(field, unique=True, name='__primary_key__')

                if SQLColumnDef.unique in col.col_constraints:
                    self.db[table].create_index(field, unique=True)

                if (SQLColumnDef.not_null in col.col_constraints or
                        SQLColumnDef.null in col.col_constraints):
                    print_warn('NULL, NOT NULL column validation check')

        if _set:
            update['$set'] = _set
        if push:
            update['$push'] = push
        if update:
            self.db['__schema__'].update_one(
                filter=_filter,
                update=update,
                upsert=True
            )

    def parse(self):
        statement = SQLStatement(self.statement)
        statement.skip(2)
        tok = statement.next()
        if tok.match(tokens.Keyword, 'TABLE'):
            self._create_table(statement)
        elif tok.match(tokens.Keyword, 'DATABASE'):
            pass
        else:
            logger.debug('Not supported {}'.format(self.statement))
            raise SQLDecodeError


class DropQuery(DMLQuery):

    def parse(self):
        statement = SQLStatement(self.statement)
        statement.skip(2)
        tok = statement.next()
        if tok.match(tokens.Keyword, 'DATABASE'):
            tok = statement.next()
            db_name = tok.get_name()
            self.cli_con.drop_database(db_name)
        elif tok.match(tokens.Keyword, 'TABLE'):
            tok = statement.next()
            table_name = tok.get_name()
            self.db.drop_collection(table_name)
        else:
            raise SQLDecodeError('statement:{}'.format(statement))

    def _execute(self):
        return


class DeleteQuery(DMLQuery):

    def __init__(self, *args):
        self.result = None
        self.kw = None
        super().__init__(*args)

    def parse(self):
        statement = SQLStatement(self.statement)
        self.kw = kw = {'filter': {}}
        statement.skip(4)
        sql_token = SQLToken.token2sql(statement.next(), self)
        self.left_table = sql_token.table

        tok = statement.next()
        if isinstance(tok, Where):
            where = WhereConverter(self, statement)
            kw.update(where.to_mongo())

    def _execute(self):
        db_con = self.db
        self.result = db_con[self.left_table].delete_many(**self.kw)
        logger.debug('delete_many: {}'.format(self.result.deleted_count))

    def count(self):
        return self.result.deleted_count


type query_types = (
        SelectQuery |
        UpdateQuery |
        InsertQuery |
        DeleteQuery |
        CreateQuery |
        DropQuery |
        AlterQuery
)


Query.FUNC_MAP = {
    'SELECT': SelectQuery,
    'UPDATE': UpdateQuery,
    'INSERT': InsertQuery,
    'DELETE': DeleteQuery,
    'CREATE': CreateQuery,
    'DROP': DropQuery,
    'ALTER': AlterQuery
}