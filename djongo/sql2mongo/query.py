"""
Module with constants and mappings to build MongoDB queries from
SQL constructors.
"""

from dataclasses import dataclass
from pymongo.cursor import Cursor as BasicCursor
from pymongo.command_cursor import CommandCursor
from pymongo.database import Database
from pymongo import MongoClient
from logging import getLogger
import re
import typing
from pymongo import ReturnDocument
from pymongo.errors import OperationFailure
from sqlparse import parse as sqlparse
from sqlparse import tokens
from sqlparse.sql import (
    IdentifierList, Identifier, Parenthesis,
    Where, Token,
    Statement)

from . import SQLDecodeError, SQLToken, MigrationError
from .converters import (
    ColumnSelectConverter, AggColumnSelectConverter, FromConverter, WhereConverter,
    AggWhereConverter, InnerJoinConverter, OuterJoinConverter, LimitConverter, AggLimitConverter, OrderConverter,
    SetConverter, AggOrderConverter, DistinctConverter, NestedInQueryConverter, GroupbyConverter, OffsetConverter, AggOffsetConverter)

logger = getLogger(__name__)


@dataclass
class CountFunc:
    table_name: str
    column_name: str
    alias_name: str = None


@dataclass
class CountDistinctFunc:
    table_name: str
    column_name: str
    alias_name: str = None


@dataclass
class CountWildcardFunc:
    alias_name: str = None



def parse(
        client_conn: MongoClient,
        db_conn: Database,
        sql: str,
        params: list
):
    return Result(client_conn, db_conn, sql, params)


class Query:
    def __init__(
            self,
            db_ref: Database,
            statement: Statement,
            params: list

    ):
        self.statement = statement
        self.db_ref = db_ref
        self.params = params

        self.alias2op: typing.Dict[str, typing.Any] = {}
        self.nested_query: NestedInQueryConverter = None

        self.left_table: typing.Optional[str] = None

        self._cursor = None
        self.parse()

    def __iter__(self):
        return
        yield

    def parse(self):
        raise NotImplementedError

    def count(self):
        raise NotImplementedError


class SelectQuery(Query):

    def __init__(self, *args):
        self.selected_columns: ColumnSelectConverter = None
        self.where: typing.Optional[WhereConverter] = None
        self.joins: typing.Optional[typing.List[
            typing.Union[InnerJoinConverter, OuterJoinConverter]
        ]] = []
        self.order: OrderConverter = None
        self.offset: OffsetConverter = None
        self.limit: typing.Optional[LimitConverter] = None
        self.distinct: DistinctConverter = None
        self.groupby: GroupbyConverter = None

        self._cursor: typing.Union[BasicCursor, CommandCursor] = None
        super().__init__(*args)

    def parse(self):
        tok_id = 0
        tok = self.statement[0]

        while tok_id is not None:
            if tok.match(tokens.DML, 'SELECT'):
                c = self.selected_columns = ColumnSelectConverter(self, tok_id)

            elif tok.match(tokens.Keyword, 'FROM'):
                c = FromConverter(self, tok_id)

            elif tok.match(tokens.Keyword, 'LIMIT'):
                c = self.limit = LimitConverter(self, tok_id)

            elif tok.match(tokens.Keyword, 'ORDER'):
                c = self.order = OrderConverter(self, tok_id)

            elif tok.match(tokens.Keyword, 'OFFSET'):
                c = self.offset = OffsetConverter(self, tok_id)

            elif tok.match(tokens.Keyword, 'INNER JOIN'):
                c = InnerJoinConverter(self, tok_id)
                self.joins.append(c)

            elif tok.match(tokens.Keyword, 'LEFT OUTER JOIN'):
                c = OuterJoinConverter(self, tok_id)
                self.joins.append(c)

            elif tok.match(tokens.Keyword, 'GROUP BY'):
                c = self.groupby = GroupbyConverter(self, tok_id)

            elif isinstance(tok, Where):
                c = self.where = WhereConverter(self, tok_id)

            else:
                raise SQLDecodeError

            tok_id, tok = self.statement.token_next(c.end_id)

    def __iter__(self):

        if self._cursor is None:
            self._cursor = self._get_cursor()

        cursor = self._cursor
        if self.selected_columns.return_const is not None:
            if not cursor.alive:
                yield []
                return
            for doc in cursor:
                yield (doc['_const'],)
            return

        elif self.selected_columns.return_count:
            if not cursor.alive:
                yield (0,)
                return
            for doc in cursor:
                yield (doc['_count'],)
            return

        for doc in cursor:
            if isinstance(cursor, BasicCursor):
                if len(doc) - 1 == len(self.selected_columns.sql_tokens):
                    doc.pop('_id')
                    yield tuple(doc.values())
                else:
                    yield self._align_results(doc)
            else:
                yield self._align_results(doc)
        return

    def count(self):

        if self._cursor is None:
            self._cursor = self._get_cursor()

        if isinstance(self._cursor, BasicCursor):
            return self._cursor.count()
        else:
            return len(list(self._cursor))

    def _needs_aggregation(self):
        return (
            self.nested_query
            or self.joins
            or self.distinct
            or self.selected_columns.return_const
            or self.selected_columns.return_count
        )

    def _make_pipeline(self):
        pipeline = []
        for join in self.joins:
            pipeline.extend(join.to_mongo())

        if self.nested_query:
            pipeline.extend(self.nested_query.to_mongo())

        if self.where:
            self.where.__class__ = AggWhereConverter
            pipeline.append(self.where.to_mongo())

        if self.distinct:
            pipeline.extend(self.distinct.to_mongo())

        if self.order:
            self.order.__class__ = AggOrderConverter
            pipeline.append(self.order.to_mongo())

        if self.limit:
            self.limit.__class__ = AggLimitConverter
            pipeline.append(self.limit.to_mongo())

        if self.offset:
            self.offset.__class__ = AggOffsetConverter
            pipeline.append(self.offset.to_mongo())

        if not self.distinct and self.selected_columns:
            self.selected_columns.__class__ = AggColumnSelectConverter
            pipeline.append(self.selected_columns.to_mongo())

        return pipeline

    def _get_cursor(self):
        if self._needs_aggregation():
            pipeline = self._make_pipeline()
            cur = self.db_ref[self.left_table].aggregate(pipeline)

        else:
            kwargs = {}
            if self.where:
                kwargs.update(self.where.to_mongo())

            if self.selected_columns:
                kwargs.update(self.selected_columns.to_mongo())

            if self.limit:
                kwargs.update(self.limit.to_mongo())

            if self.order:
                kwargs.update(self.order.to_mongo())
            if self.offset:
                kwargs.update(self.offset.to_mongo())

            cur = self.db_ref[self.left_table].find(**kwargs)

        return cur

    def _align_results(self, doc):
        ret = []
        if self.distinct:
            sql_tokens = self.distinct.sql_tokens
        else:
            sql_tokens = self.selected_columns.sql_tokens

        for selected in sql_tokens:
            if selected.table == self.left_table:
                try:
                    ret.append(doc[selected.column])
                except KeyError:
                    raise MigrationError(selected.column)
            else:
                try:
                    ret.append(doc[selected.table][selected.column])
                except KeyError:
                    raise MigrationError(selected.column)

        return tuple(ret)


class UpdateQuery(Query):

    def __init__(self, *args):
        self.selected_table: ColumnSelectConverter = None
        self.set_columns: SetConverter = None
        self.where: WhereConverter = None
        self.result = None
        super().__init__(*args)

    def count(self):
        return self.result.matched_count

    def parse(self):
        db = self.db_ref
        tok_id = 0
        tok: Token = self.statement[0]

        while tok_id is not None:
            if tok.match(tokens.DML, 'UPDATE'):
                c = ColumnSelectConverter(self, tok_id)
                self.left_table = c.sql_tokens[0].table

            elif tok.match(tokens.Keyword, 'SET'):
                c = self.set_columns = SetConverter(self, tok_id)

            elif isinstance(tok, Where):
                c = self.where = WhereConverter(self, tok_id)

            else:
                raise SQLDecodeError

            tok_id, tok = self.statement.token_next(c.end_id)

        kwargs = {}
        if self.where:
            kwargs.update(self.where.to_mongo())

        kwargs.update(self.set_columns.to_mongo())
        self.result = db[self.left_table].update_many(**kwargs)
        logger.debug(f'update_many: {self.result.modified_count}, matched: {self.result.matched_count}')


class InsertQuery(Query):

    def __init__(self, result_ref: 'Result', *args):
        self._result_ref = result_ref
        super().__init__(*args)

    def parse(self):
        db = self.db_ref
        sm = self.statement
        insert = {}

        nextid, nexttok = sm.token_next(2)
        if isinstance(nexttok, Identifier):
            collection = nexttok.get_name()
            self.left_table = collection
            auto = db['__schema__'].find_one_and_update(
                {
                    'name': collection,
                    'auto': {
                        '$exists': True
                    }
                },
                {'$inc': {'auto.seq': 1}},
                return_document=ReturnDocument.AFTER
            )

            if auto:
                auto_field_id = auto['auto']['seq']
                for name in auto['auto']['field_names']:
                    insert[name] = auto_field_id
            else:
                auto_field_id = None
        else:
            raise SQLDecodeError

        nextid, nexttok = sm.token_next(nextid)

        if isinstance(nexttok[1], IdentifierList):
            for an_id in nexttok[1].get_identifiers():
                sql = SQLToken(an_id, None)
                insert[sql.column] = self.params.pop(0)
        else:
            sql = SQLToken(nexttok[1], None)
            insert[sql.column] = self.params.pop(0)

        if self.params:
            raise SQLDecodeError

        result = db[collection].insert_one(insert)
        if not auto_field_id:
            auto_field_id = str(result.inserted_id)

        self._result_ref.last_row_id = auto_field_id
        logger.debug('insert id {}'.format(result.inserted_id))


class DeleteQuery(Query):

    def __init__(self, *args):
        self.result = None
        super().__init__(*args)

    def parse(self):
        db_con = self.db_ref
        sm = self.statement
        kw = {}

        tok_id, tok = sm.token_next(2)
        sql_token = SQLToken(tok, None)
        collection = sql_token.table

        self.left_table = sql_token.table

        tok_id, tok = sm.token_next(tok_id)
        if tok_id and isinstance(tok, Where):
            where = WhereConverter(self, tok_id)
            kw.update(where.to_mongo())

        self.result = db_con[collection].delete_many(**kw)
        logger.debug('delete_many: {}'.format(self.result.deleted_count))

    def count(self):
        return self.result.deleted_count


class Result:

    def __init__(self,
                 client_connection: MongoClient,
                 db_connection: Database,
                 sql: str,
                 params: typing.Optional[list]):
        logger.debug('params: {}'.format(params))

        self._params = params
        self.db = db_connection
        self.cli_con = client_connection
        self._params_index_count = -1
        self._sql = re.sub(r'%s', self._param_index, sql)
        self.last_row_id = None
        self._result_generator = None

        self._query = None
        self.parse()

    def count(self):
        return self._query.count()

    def close(self):
        if self._query and self._query._cursor:
            self._query._cursor.close()

    def __next__(self):
        if self._result_generator is None:
            self._result_generator = iter(self)

        return next(self._result_generator)

    next = __next__

    def __iter__(self):
        try:
            yield from iter(self._query)

        except OperationFailure as e:
            import djongo
            exe = SQLDecodeError(
                f'FAILED SQL: {self._sql}\n' 
                f'Pymongo error: {e.details}\n'
                f'Version: {djongo.__version__}'
            )
            raise exe from e

        except Exception as e:
            import djongo
            exe = SQLDecodeError(
                f'FAILED SQL: {self._sql}\n'
                f'Version: {djongo.__version__}'
            )
            raise exe from e

    def _param_index(self, _):
        self._params_index_count += 1
        return '%({})s'.format(self._params_index_count)

    def parse(self):
        logger.debug(f'\n sql_command: {self._sql}')
        statement = sqlparse(self._sql)
        if len(statement) > 1:
            raise SQLDecodeError(self._sql)

        statement = statement[0]
        sm_type = statement.get_type()

        try:
            handler = self.FUNC_MAP[sm_type]
        except KeyError:
            logger.debug('\n Not implemented {} {}'.format(sm_type, statement))
            raise NotImplementedError(f'{sm_type} command not implemented for SQL {self._sql}')

        else:
            try:
                return handler(self, statement)

            except OperationFailure as e:
                import djongo
                exe = SQLDecodeError(
                    f'FAILED SQL: {self._sql}\n'
                    f'Pymongo error: {e.details}\n'
                    f'Version: {djongo.__version__}'
                )
                raise exe from e

            except Exception as e:
                import djongo
                exe = SQLDecodeError(
                    f'FAILED SQL: {self._sql}'
                    f'Version: {djongo.__version__}'
                )
                raise exe from e

    def _alter(self, sm):
        tok_id, tok = sm.token_next(0)
        if tok.match(tokens.Keyword, 'TABLE'):
            tok_id, tok = sm.token_next(tok_id)
            if not tok:
                logger.debug('Not implemented command not implemented for SQL {}'.format(self._sql))
                return

            table = SQLToken(tok, None).table

            tok_id, tok = sm.token_next(tok_id)
            if (not tok
                    or not tok.match(tokens.Keyword, 'ADD')):
                logger.debug('Not implemented command not implemented for SQL {}'.format(self._sql))
                return

            tok_id, tok = sm.token_next(tok_id)
            if (not tok
                    or not tok.match(tokens.Keyword, 'CONSTRAINT')):
                logger.debug('Not implemented command not implemented for SQL {}'.format(self._sql))
                return

            tok_id, tok = sm.token_next(tok_id)
            if not isinstance(tok, Identifier):
                logger.debug('Not implemented command not implemented for SQL {}'.format(self._sql))
                return

            constraint_name = tok.get_name()

            tok_id, tok = sm.token_next(tok_id)
            if not tok.match(tokens.Keyword, 'UNIQUE'):
                logger.debug('Not implemented command not implemented for SQL {}'.format(self._sql))
                return

            tok_id, tok = sm.token_next(tok_id)
            if isinstance(tok, Parenthesis):
                index = [(field.strip(' "'), 1) for field in tok.value.strip('()').split(',')]
                self.db[table].create_index(index, unique=True, name=constraint_name)
            else:
                raise NotImplementedError('Alter command not implemented for SQL {}'.format(self._sql))

    def _create(self, sm):
        tok_id, tok = sm.token_next(0)
        if tok.match(tokens.Keyword, 'TABLE'):
            if '__schema__' not in self.db.collection_names(include_system_collections=False):
                self.db.create_collection('__schema__')
                self.db['__schema__'].create_index('name', unique=True)
                self.db['__schema__'].create_index('auto')

            tok_id, tok = sm.token_next(tok_id)
            table = SQLToken(tok, None).table
            self.db.create_collection(table)
            logger.debug('Created table {}'.format(table))

            tok_id, tok = sm.token_next(tok_id)
            if isinstance(tok, Parenthesis):
                _filter = {
                    'name': table
                }
                _set = {}
                push = {}
                update = {}

                for col in tok.value.strip('()').split(','):
                    field = col[col.find('"') + 1: col.rfind('"')]

                    if col.find('AUTOINCREMENT') != -1:
                        try:
                            push['auto.field_names']['$each'].append(field)
                        except KeyError:
                            push['auto.field_names'] = {
                                '$each': [field]
                            }

                        _set['auto.seq'] = 0

                    if col.find('PRIMARY KEY') != -1:
                        self.db[table].create_index(field, unique=True, name='__primary_key__')

                    if col.find('UNIQUE') != -1:
                        self.db[table].create_index(field, unique=True)

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

        elif tok.match(tokens.Keyword, 'DATABASE'):
            pass
        else:
            logger.debug('Not supported {}'.format(sm))

    def _drop(self, sm):
        tok_id, tok = sm.token_next(0)
        if tok.match(tokens.Keyword, 'DATABASE'):
            tok_id, tok = sm.token_next(tok_id)
            db_name = tok.get_name()
            self.cli_con.drop_database(db_name)
        elif tok.match(tokens.Keyword, 'TABLE'):
            tok_id, tok = sm.token_next(tok_id)
            table_name = tok.get_name()
            self.db.drop_collection(table_name)
        else:
            raise SQLDecodeError('statement:{}'.format(sm))

    def _update(self, sm):
        self._query = UpdateQuery(self.db, sm, self._params)

    def _delete(self, sm):
        self._query = DeleteQuery(self.db, sm, self._params)

    def _insert(self, sm):
        self._query = InsertQuery(self, self.db, sm, self._params)

    def _select(self, sm):
        self._query = SelectQuery(self.db, sm, self._params)

    FUNC_MAP = {
        'SELECT': _select,
        'UPDATE': _update,
        'INSERT': _insert,
        'DELETE': _delete,
        'CREATE': _create,
        'DROP': _drop,
        'ALTER': _alter
    }

# TODO: Need to do this


