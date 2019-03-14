"""
Module with constants and mappings to build MongoDB queries from
SQL constructors.
"""

import re
import typing
from logging import getLogger

from dataclasses import dataclass
from pymongo import MongoClient
from pymongo import ReturnDocument
from pymongo.command_cursor import CommandCursor
from pymongo.cursor import Cursor as BasicCursor
from pymongo.database import Database
from pymongo.errors import OperationFailure, CollectionInvalid
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
    SetConverter, AggOrderConverter, DistinctConverter, NestedInQueryConverter, GroupbyConverter, OffsetConverter,
    AggOffsetConverter, HavingConverter)

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



class Query:
    def __init__(
            self,
            db_ref: Database,
            connection_properties: 'djongo.base.DjongoClient',
            statement: Statement,
            params: list

    ):
        self.statement = statement
        self.db_ref = db_ref
        self.connection_properties = connection_properties
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


class VoidQuery(Query):

    def execute(self):
        raise NotImplementedError

    def count(self):
        pass


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
        self.having: HavingConverter = None


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

            elif tok.match(tokens.Keyword, 'GROUP'):
                c = self.groupby = GroupbyConverter(self, tok_id)

            elif tok.match(tokens.Keyword, 'HAVING'):
                c = self.having = HavingConverter(self, tok_id)

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
            or self.groupby
            or self.selected_columns.return_const
            or self.selected_columns.return_count
            or self.selected_columns.has_func
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

        if self.groupby:
            pipeline.extend(self.groupby.to_mongo())

        if self.having:
            pipeline.append(self.having.to_mongo())

        if self.distinct:
            pipeline.extend(self.distinct.to_mongo())

        if self.order:
            self.order.__class__ = AggOrderConverter
            pipeline.append(self.order.to_mongo())

        if self.offset:
            self.offset.__class__ = AggOffsetConverter
            pipeline.append(self.offset.to_mongo())

        if self.limit:
            self.limit.__class__ = AggLimitConverter
            pipeline.append(self.limit.to_mongo())

        if (
            not (
                self.distinct
                or self.groupby
            )
            and self.selected_columns
        ):
            self.selected_columns.__class__ = AggColumnSelectConverter
            pipeline.append(self.selected_columns.to_mongo())

        return pipeline

    def _get_cursor(self):
        if self._needs_aggregation():
            pipeline = self._make_pipeline()
            cur = self.db_ref[self.left_table].aggregate(pipeline)
            logger.debug(f'Aggregation query: {pipeline}')
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
            logger.debug(f'Find query: {kwargs}')

        return cur

    def _align_results(self, doc):
        ret = []
        if self.distinct:
            sql_tokens = self.distinct.sql_tokens
        else:
            sql_tokens = self.selected_columns.sql_tokens

        for selected in sql_tokens:
            if isinstance(selected, SQLToken):
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


class InsertQuery(VoidQuery):
    DEFAULT = object()

    def __init__(self, result_ref: 'Result', *args):
        self._result_ref = result_ref
        self._cols = None
        self._vals = None
        super().__init__(*args)

    def _table(self, tok_id):
        tok_id, tok = self.statement.token_next(tok_id)
        collection = tok.get_name()
        if collection not in self.connection_properties.cached_collections:
            if self.connection_properties.enforce_schema:
                raise MigrationError(collection)
            self.connection_properties.cached_collections.add(collection)

        self.left_table = collection
        return tok_id

    def _columns(self, tok_id):
        tok_id, tok = self.statement.token_next(tok_id)
        if isinstance(tok[1], IdentifierList):
            self._cols = [
                SQLToken(an_id, None).column
                for an_id in tok[1].get_identifiers()
            ]
        else:
            self._cols = [SQLToken(tok[1], None).column]

        return tok_id

    def _values(self, tok_id):
        tok_id, tok = self.statement.token_next(tok_id)
        self._vals = []
        while tok_id is not None:
            if tok.match(tokens.Keyword, 'VALUES'):
                pass
            elif isinstance(tok, Parenthesis):
                if isinstance(tok[1], IdentifierList):
                    self._vals.append(
                        tuple(
                            self.params[i] if i is not None else None
                            for i in SQLToken(tok, None)
                        )
                    )
                else:
                    if tok[1].match(tokens.Keyword, 'DEFAULT'):
                        self._vals.append((self.DEFAULT,))
                    else:
                        i = next(iter(SQLToken(tok)))
                        self._vals.append(
                            (self.params[i] if i is not None else None,)
                        )

            tok_id, tok = self.statement.token_next(tok_id)

    def execute(self):
        docs = []
        num = len(self._vals)

        auto = self.db_ref['__schema__'].find_one_and_update(
            {
                'name': self.left_table,
                'auto': {
                    '$exists': True
                }
            },
            {'$inc': {'auto.seq': num}},
            return_document=ReturnDocument.AFTER
        )

        for i, val in enumerate(self._vals):
            ins = {}
            if auto:
                for name in auto['auto']['field_names']:
                    ins[name] = auto['auto']['seq'] - num + i + 1
            for fld, v in zip(self._cols, val):
                if (auto
                    and fld in auto['auto']['field_names']
                    and v == self.DEFAULT
                ):
                    continue
                ins[fld] = v
            docs.append(ins)

        res = self.db_ref[self.left_table].insert_many(docs, ordered=False)
        if auto:
            self._result_ref.last_row_id = auto['auto']['seq']
        else:
            self._result_ref.last_row_id = res.inserted_ids[-1]
        logger.debug('insert ids {}'.format(res.inserted_ids))

    def parse(self):

        tok_id = self._table(2)
        tok_id = self._columns(tok_id)
        self._values(tok_id)
    #     tok_id, tok = sm.token_next(tok_id)
    #
    #     if isinstance(tok, Identifier):
    #         self.collection = collection = tok.get_name()
    #
    #     if collection not in self.connection_properties.cached_collections:
    #         if self.connection_properties.enforce_schema:
    #             raise MigrationError(collection)
    #         self.connection_properties.cached_collections.add(collection)
    #
    #     self.left_table = collection
    #     auto = db['__schema__'].find_one_and_update(
    #         {
    #             'name': collection,
    #             'auto': {
    #                 '$exists': True
    #             }
    #         },
    #         {'$inc': {'auto.seq': 1}},
    #         return_document=ReturnDocument.AFTER
    #     )
    #
    #     if auto:
    #         auto_field_id = auto['auto']['seq']
    #         for name in auto['auto']['field_names']:
    #             insert[name] = auto_field_id
    #     else:
    #         auto_field_id = None
    # else:
    #     raise SQLDecodeError
    #
    #     nextid, coltok = sm.token_next(nextid)
    #     nextid, nexttok = sm.token_next(nextid)
    #     if not nexttok.match(tokens.Keyword, 'VALUES'):
    #         raise SQLDecodeError
    #
    #     nextid, placeholder = sm.token_next(nextid)
    #
    #     if isinstance(coltok[1], IdentifierList):
    #         for an_id, i in zip(coltok[1].get_identifiers(), SQLToken(placeholder)):
    #             sql = SQLToken(an_id, None)
    #             insert[sql.column] = self.params[i] if i is not None else None
    #
    #     else:
    #         sql = SQLToken(coltok[1], None)
    #         if placeholder[1].match(tokens.Keyword, 'DEFAULT'):
    #             if sql.column == 'id':
    #                 pass
    #             else:
    #                 raise SQLDecodeError
    #         else:
    #             i = next(iter(SQLToken(placeholder)))
    #             insert[sql.column] = self.params[i] if i is not None else None
    #
    #     result = db[collection].insert_one(insert)
    #     if not auto_field_id:
    #         auto_field_id = result.inserted_id
    #
    #     self._result_ref.last_row_id = auto_field_id
    #     logger.debug('insert id {}'.format(result.inserted_id))


class AlterQuery(VoidQuery):

    def __init__(self, *args):
        self._iden_name = None
        self._old_column = None
        self._new_column = None
        self._default = None
        self._cascade = None
        self._null = None

        super().__init__(*args)

    def parse(self):
        sm = self.statement
        tok_id = 0
        tok_id, tok = sm.token_next(tok_id)

        while tok_id is not None:
            if tok.match(tokens.Keyword, 'TABLE'):
                tok_id = self._table(tok_id)
            elif tok.match(tokens.Keyword, 'ADD'):
                tok_id = self._add(tok_id)
            elif tok.match(tokens.Keyword, 'FLUSH'):
                self.execute = self._flush
            elif tok.match(tokens.Keyword.DDL, 'DROP'):
                tok_id = self._drop(tok_id)
            elif tok.match(tokens.Keyword.DDL, 'ALTER'):
                tok_id = self._alter(tok_id)
            elif tok.match(tokens.Keyword, 'RENAME'):
                tok_id = self._rename(tok_id)
            else:
                raise NotImplementedError

            tok_id, tok = sm.token_next(tok_id)

    def _rename(self, tok_id):
        sm = self.statement
        tok_id, tok = sm.token_next(tok_id)

        to = False
        while tok_id is not None:
            if tok.match(tokens.Keyword, ('COLUMN'),):
                self.execute = self._rename_column
            if tok.match(tokens.Keyword, ('TO'),):
                to = True
            elif isinstance(tok, Identifier):
                if not to:
                    self.old_column = tok.get_real_name()
                else:
                    self.new_column = tok.get_real_name()

            tok_id, tok = sm.token_next(tok_id)

        return tok_id

    def _rename_column(self):
        self.db_ref[self.left_table].update(
            {},
            {
                '$rename': {
                    self.old_column: self.new_column
                }
            },
            multi=True
        )

    def _alter(self, tok_id):
        self.execute = lambda: None

    def _flush(self):
        self.db_ref[self.left_table].delete_many({})

    def _table(self, tok_id):
        sm = self.statement
        tok_id, tok = sm.token_next(tok_id)
        if not tok:
            raise SQLDecodeError
        self.left_table = SQLToken(tok, None).table
        return tok_id

    def _drop(self, tok_id):
        sm = self.statement
        tok_id, tok = sm.token_next(tok_id)

        while tok_id is not None:
            if tok.match(tokens.Keyword, (
                'CASCADE'
            )):
                pass
            elif isinstance(tok, Identifier):
                self._iden_name = tok.get_real_name()
            elif tok.match(tokens.Keyword, 'CONSTRAINT'):
                self.execute = self._drop_constraint
            elif tok.match(tokens.Keyword, 'COLUMN'):
                self.execute = self._drop_column
            else:
                raise NotImplementedError

            tok_id, tok = sm.token_next(tok_id)

        return tok_id

    def _drop_constraint(self):
        self.db_ref[self.left_table].drop_index(self._iden_name)

    def _drop_column(self):
        self.db_ref[self.left_table].update(
            {},
            {
                '$unset': {
                    self._iden_name: ''
                }
            },
            multi=True
        )

    def _add(self, tok_id):
        sm = self.statement
        tok_id, tok = sm.token_next(tok_id)

        while tok_id is not None:
            if tok.match(tokens.Keyword, (
                'CONSTRAINT', 'KEY', 'REFERENCES',
                'NOT NULL', 'NULL'
            )):
                pass
            elif tok.match(tokens.Name.Builtin, (
                'integer', 'bool', 'char', 'date',
                'datetime', 'float', 'time'
            )):
                pass
            elif isinstance(tok, Identifier):
                self._iden_name = tok.get_real_name()
            elif isinstance(tok, Parenthesis):
                self.field_dir = [
                    (field.strip(' "'), 1)
                    for field in tok.value.strip('()').split(',')
                ]
            elif tok.match(tokens.Keyword, 'DEFAULT'):
                tok_id, tok = sm.token_next(tok_id)
                i = SQLToken.placeholder_index(tok)
                self._default = self.params[i]
            elif tok.match(tokens.Keyword, 'UNIQUE'):
                self.execute = self._unique
            elif tok.match(tokens.Keyword, 'INDEX'):
                self.execute = self._index
            elif tok.match(tokens.Keyword, 'FOREIGN'):
                self.execute = self._fk
            elif tok.match(tokens.Keyword, 'COLUMN'):
                self.execute = self._add_column
            else:
                raise NotImplementedError

            tok_id, tok = sm.token_next(tok_id)

        return tok_id

    def _add_column(self):
        self.db_ref[self.left_table].update(
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
            multi=True
        )
    def _index(self):
        self.db_ref[self.left_table].create_index(
            self.field_dir,
            name=self._iden_name)

    def _unique(self):
        self.db_ref[self.left_table].create_index(
            self.field_dir,
            unique=True,
            name=self._iden_name)

    def _fk(self):
        pass


class DeleteQuery(Query):

    def __init__(self, *args):
        self.result = None
        super().__init__(*args)

    def parse(self):
        db_con = self.db_ref
        sm = self.statement
        kw = {'filter': {}}

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
                 connection_properties: 'base.DjongoClient',
                 sql: str,
                 params: typing.Optional[list]):
        logger.debug('params: {}'.format(params))

        self._params = params
        self.db = db_connection
        self.cli_con = client_connection
        self.connection_properties = connection_properties
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

        except MigrationError:
            raise

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

            except MigrationError:
                raise

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

    def _alter(self, sm):
        try:
            self._query = AlterQuery(self.db, self.connection_properties, sm, self._params)
        except NotImplementedError:
            logger.debug('Not implemented alter command for SQL {}'.format(self._sql))
        else:
            self._query.execute()

    def _create(self, sm):
        tok_id, tok = sm.token_next(0)
        if tok.match(tokens.Keyword, 'TABLE'):
            if '__schema__' not in self.connection_properties.cached_collections:
                self.db.create_collection('__schema__')
                self.connection_properties.cached_collections.add('__schema__')
                self.db['__schema__'].create_index('name', unique=True)
                self.db['__schema__'].create_index('auto')

            tok_id, tok = sm.token_next(tok_id)
            table = SQLToken(tok, None).table
            try:
                self.db.create_collection(table)
            except CollectionInvalid:
                if self.connection_properties.enforce_schema:
                    raise
                else:
                    return

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
                    props = col.strip().split(' ')
                    field = props[0].strip('"')
                    type_code = props[1]

                    _set[f'fields.{field}'] = {
                        'type_code': type_code
                    }

                    if field == '_id':
                        continue

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
        self._query = UpdateQuery(self.db, self.connection_properties, sm, self._params)

    def _delete(self, sm):
        self._query = DeleteQuery(self.db, self.connection_properties, sm, self._params)

    def _insert(self, sm):
        self._query = InsertQuery(self, self.db, self.connection_properties, sm, self._params)
        self._query.execute()

    def _select(self, sm):
        self._query = SelectQuery(self.db, self.connection_properties, sm, self._params)

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


