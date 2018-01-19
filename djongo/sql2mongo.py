from itertools import chain

from dataclasses import dataclass
from pymongo.cursor import Cursor as BasicCursor
from pymongo.command_cursor import CommandCursor
from pymongo.database import Database
from pymongo import MongoClient
from logging import getLogger
import re
import typing
from pymongo import ReturnDocument, ASCENDING, DESCENDING
from pymongo.errors import OperationFailure
from sqlparse import parse as sqlparse
from sqlparse import tokens
from sqlparse.sql import (
    IdentifierList, Identifier, Parenthesis,
    Where, Comparison, Function, Token,
    Statement)
from collections import OrderedDict

logger = getLogger(__name__)

OPERATOR_MAP = {
    '=': '$eq',
    '>': '$gt',
    '<': '$lt',
    '>=': '$gte',
    '<=': '$lte',
}

OPERATOR_PRECEDENCE = {
    'LIKE': 6,
    'IN': 5,
    'NOT IN': 4,
    'NOT': 3,
    'AND': 2,
    'OR': 1,
    'generic': 0
}

ORDER_BY_MAP = {
    'ASC': ASCENDING,
    'DESC': DESCENDING
}


class SQLDecodeError(ValueError):

    def __init__(self, err_sql=None):
        self.err_sql = err_sql


@dataclass
class TableColumnOp:
    table_name: str
    column_name: str
    alias_name: str = None


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


class DistinctOp(typing.NamedTuple):
    table_name: str
    column_name: str
    alias_name: str = None


def parse(
        client_conn: MongoClient,
        db_conn: Database,
        sql: str,
        params: list
):
    return Result(client_conn, db_conn, sql, params)


def re_index(value: str):
    match = re.match(r'%\(([0-9]+)\)s', value, flags=re.IGNORECASE)
    if match:
        index = int(match.group(1))
    else:
        match = re.match(r'NULL', value, flags=re.IGNORECASE)
        if not match:
            raise SQLDecodeError
        index = None
    return index


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
        self.nested_query: NestedInQuery = None

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


class Converter:
    def __init__(
            self,
            query: typing.Union['SelectQuery', Query],
            begin_id: int
    ):
        self.query = query
        self.begin_id = begin_id
        self.end_id = None
        self.parse()

    def parse(self):
        raise NotImplementedError

    def to_mongo(self):
        raise NotImplementedError


class ColumnSelectConverter(Converter):
    def __init__(self, query, begin_id):
        self.select_all = False
        self.return_const = None
        self.return_count = False
        self.num_columns = 0

        self.sql_tokens: typing.List[SQLToken] = []
        super().__init__(query, begin_id)

    def parse(self):
        tok_id, tok = self.query.statement.token_next(self.begin_id)
        if tok.value == '*':
            self.select_all = True

        elif isinstance(tok, Identifier):
            self._identifier(tok)

        elif isinstance(tok, IdentifierList):
            for atok in tok.get_identifiers():
                self._identifier(atok)

        elif tok.match(tokens.Keyword, 'DISTINCT'):
            self.query.distinct = DistinctConverter(self.query, tok_id)
            tok_id = self.query.distinct.end_id

        else:
            raise SQLDecodeError

        self.end_id = tok_id

    def _identifier(self, tok):
        if isinstance(tok[0], Parenthesis):
            self.return_const = int(tok[0][1].value)
            return

        elif isinstance(tok[0], Function):
            if tok[0][0].value == 'COUNT':
                self.return_count = True

        else:
            sql = SQLToken(tok, self.query.alias2op)
            self.sql_tokens.append(sql)
            if sql.alias:
                self.query.alias2op[sql.alias] = sql

    def to_mongo(self):
        doc = [selected.column for selected in self.sql_tokens]
        return {'projection': doc}


class AggColumnSelectConverter(ColumnSelectConverter):

    def to_mongo(self):
        project = {}
        if self.return_const is not None:
            project['const'] = {'$literal': self.return_const}

        elif self.return_count:
            return {'$count': 'count'}

        else:
            for selected in self.sql_tokens:
                if selected.table == self.query.left_table:
                    project[selected.column] = True
                else:
                    project[selected.table + '.' + selected.column] = True

        return {'$project': project}


class FromConverter(Converter):

    def parse(self):
        sm = self.query.statement
        self.end_id, tok = sm.token_next(self.begin_id)
        sql = SQLToken(tok, self.query.alias2op)
        self.query.left_table = sql.table
        if sql.alias:
            self.query.alias2op[sql.alias] = sql


class WhereConverter(Converter):
    nested_op: 'WhereOp' = None
    op: 'WhereOp' = None

    def parse(self):
        sm = self.query.statement
        tok = sm[self.begin_id]
        self.op = WhereOp(
            token_id=0,
            token=tok,
            query=self.query,
            params=self.query.params
        )
        self.end_id = self.begin_id

    def to_mongo(self):
        return {'filter': self.op.to_mongo()}


class AggWhereConverter(WhereConverter):

    def to_mongo(self):
        return {'$match': self.op.to_mongo()}


class JoinConverter(Converter):
    def __init__(self, *args):
        self.left_table: str = None
        self.right_table: str = None
        self.left_column: str = None
        self.right_column: str = None
        super().__init__(*args)

    def parse(self):
        sm = self.query.statement
        tok_id, tok = sm.token_next(self.begin_id)
        sql = SQLToken(tok, self.query.alias2op)
        right_table = self.right_table = sql.table

        tok_id, tok = sm.token_next(tok_id)
        if not tok.match(tokens.Keyword, 'ON'):
            raise SQLDecodeError

        tok_id, tok = sm.token_next(tok_id)
        if isinstance(tok, Parenthesis):
            tok = tok[1]

        sql = SQLToken(tok, self.query.alias2op)
        if right_table == sql.right_table:
            self.left_table = sql.left_table
            self.left_column = sql.left_column
            self.right_column = sql.right_column
        else:
            self.left_table = sql.right_table
            self.left_column = sql.right_column
            self.right_column = sql.left_column

        self.end_id = tok_id

    def _lookup(self):
        if self.left_table == self.query.left_table:
            local_field = self.left_column
        else:
            local_field = f'{self.left_table}.{self.left_column}'

        lookup = {
            '$lookup': {
                'from': self.right_table,
                'localField': local_field,
                'foreignField': self.right_column,
                'as': self.right_table
            }
        }

        return lookup


class InnerJoinConverter(JoinConverter):

    def to_mongo(self):
        lookup = self._lookup()
        pipeline = [
            {
                '$match': {
                    self.left_column: {
                        '$ne': None,
                        '$exists': True
                    }
                }
            },
            lookup,
            {
                '$unwind': '$' + self.right_table
            }
        ]

        return pipeline


class OuterJoinConverter(JoinConverter):

    def to_mongo(self):
        lookup = self._lookup()
        pipeline = [
            lookup,
            {
                '$unwind': {
                    'path': '$' + self.right_table,
                    'preserveNullAndEmptyArrays': True
                }
            }
        ]

        return pipeline


class LimitConverter(Converter):
    def __init__(self, *args):
        self.limit: int = None
        super().__init__(*args)

    def parse(self):
        sm = self.query.statement
        self.end_id, tok = sm.token_next(self.begin_id)
        self.limit = int(tok.value)

    def to_mongo(self):
        return {'limit': self.limit}


class AggLimitConverter(LimitConverter):

    def to_mongo(self):
        return {'$limit': self.limit}


class OrderConverter(Converter):
    def __init__(self, *args):
        self.columns: typing.List[typing.Tuple[SQLToken, SQLToken]] = []
        super().__init__(*args)

    def parse(self):
        sm = self.query.statement
        tok_id, tok = sm.token_next(self.begin_id)
        if not tok.match(tokens.Keyword, 'BY'):
            raise SQLDecodeError

        tok_id, tok = sm.token_next(tok_id)
        if isinstance(tok, Identifier):
            self.columns.append((SQLToken(tok[0], self.query.alias2op), SQLToken(tok, self.query.alias2op)))

        elif isinstance(tok, IdentifierList):
            for _id in tok.get_identifiers():
                self.columns.append((SQLToken(_id[0], self.query.alias2op), SQLToken(_id, self.query.alias2op)))

        self.end_id = tok_id

    def to_mongo(self):
        sort = [(tok.column, tok_ord.order) for tok, tok_ord in self.columns]
        return {'sort': sort}


class SetConverter(Converter):

    def __init__(self, *args):
        self.sql_tokens: typing.List[SQLToken] = []
        super().__init__(*args)

    def parse(self):
        tok_id, tok = self.query.statement.token_next(self.begin_id)

        if isinstance(tok, Comparison):
            self.sql_tokens.append(SQLToken(tok, self.query.alias2op))

        elif isinstance(tok, IdentifierList):
            for atok in tok.get_identifiers():
                self.sql_tokens.append((SQLToken(atok, self.query.alias2op)))

        else:
            raise SQLDecodeError

        self.end_id = tok_id

    def to_mongo(self):
        return {
            'update': {
                '$set': {
                    sql.lhs_column: self.query.params[sql.rhs_indexes] for sql in self.sql_tokens}
            }
        }


class AggOrderConverter(OrderConverter):

    def to_mongo(self):
        sort = OrderedDict()
        for tok, tok_ord in self.columns:
            if tok.table == self.query.left_table:
                sort[tok.column] = tok_ord.order
            else:
                sort[tok.table + '.' + tok.column] = tok_ord.order

        return {'$sort': sort}


class DistinctConverter(ColumnSelectConverter):
    def __init__(self, *args):
        super().__init__(*args)

    def to_mongo(self):
        _id = {}
        for selected in self.sql_tokens:
            if selected.table == self.query.left_table:
                _id[selected.column] = '$'+selected.column
            else:
                try:
                    _id[selected.table][selected.column] = '$'+selected.table+'.'+selected.column
                except KeyError:
                    _id[selected.table] = {selected.column: '$'+selected.table+'.'+selected.column}

        return [
            {
                '$group': {
                    '_id': _id
                }
            },
            {
                '$replaceRoot': {
                    'newRoot': '$_id'
                }
            }
        ]


class NestedInQuery(Converter):

    def __init__(self, token, *args):
        self._token = token
        self._in_query: SelectQuery = None
        super().__init__(*args)

    def parse(self):
        self._in_query = SelectQuery(
            self.query.db_ref,
            sqlparse(self._token.value[1:-1])[0],
            self.query.params
        )

    def to_mongo(self):
        pipeline = [
            {
                '$lookup': {
                    'from': self._in_query.left_table,
                    'pipeline': self._in_query._make_pipeline(),
                    'as': '_nested_in'
                }
            },
            {
                '$addFields': {
                    '_nested_in': {
                        '$map': {
                            'input': '$_nested_in',
                            'as': 'lookup_result',
                            'in': '$$lookup_result.' + self._in_query.selected_columns.sql_tokens[0].column
                        }
                    }
                }
            }
        ]
        return pipeline



class SelectQuery(Query):
    def __init__(self, *args):

        self.selected_columns: ColumnSelectConverter = None
        self.where: typing.Optional[WhereConverter] = None
        self.joins: typing.Optional[typing.List[
            typing.Union[InnerJoinConverter, OuterJoinConverter]
        ]] = []
        self.order: OrderConverter = None
        self.limit: typing.Optional[LimitConverter] = None
        self.distinct: DistinctConverter = None

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

            elif tok.match(tokens.Keyword, 'INNER JOIN'):
                c = InnerJoinConverter(self, tok_id)
                self.joins.append(c)

            elif tok.match(tokens.Keyword, 'LEFT OUTER JOIN'):
                c = OuterJoinConverter(self, tok_id)
                self.joins.append(c)

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
                yield (doc['const'],)
            return

        elif self.selected_columns.return_count:
            if not cursor.alive:
                yield (0,)
                return
            for doc in cursor:
                yield (doc['count'],)
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
                    ret.append(None)  # This is a silent failure
            else:
                try:
                    ret.append(doc[selected.table][selected.column])
                except KeyError:
                    ret.append(None)  # This is a silent failure.

        return ret


class UpdateQuery(Query):

    def __init__(self, *args):
        self.selected_table: ColumnSelectConverter = None
        self.set_columns: SetConverter = None
        self.where: WhereConverter = None
        self.result = None
        super().__init__(*args)

    def count(self):
        return self.result.modified_count

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

        for aid in nexttok[1].get_identifiers():
            sql = SQLToken(aid, None)
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
            exe = SQLDecodeError(f'FAILED SQL: {self._sql}' f'Pymongo error: {e.details}')
            raise exe from e

        except Exception as e:
            exe = SQLDecodeError(f'FAILED SQL: {self._sql}')
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
                exe = SQLDecodeError(f'FAILED SQL: {self._sql}' f'Pymongo error: {e.details}')
                raise exe from e

            except Exception as e:
                exe = SQLDecodeError(f'FAILED SQL: {self._sql}')
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

        if not tok.match(tokens.Keyword, 'DATABASE'):
            raise SQLDecodeError('statement:{}'.format(sm))

        tok_id, tok = sm.token_next(tok_id)
        db_name = tok.get_name()
        self.cli_con.drop_database(db_name)

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


class SQLToken:

    def __init__(self, token: Token, alias2op=None):
        self._token = token
        self.alias2op: typing.Dict[str, SQLToken] = alias2op

    @property
    def table(self):
        if not isinstance(self._token, Identifier):
            raise SQLDecodeError

        name = self._token.get_parent_name()
        if name is None:
            name = self._token.get_real_name()
        else:
            if name in self.alias2op:
                return self.alias2op[name].table
            return name

        if name is None:
            raise SQLDecodeError

        if self.alias2op and name in self.alias2op:
            return self.alias2op[name].table
        return name

    @property
    def column(self):
        if not isinstance(self._token, Identifier):
            raise SQLDecodeError

        name = self._token.get_real_name()
        if name is None:
            raise SQLDecodeError
        return name

    @property
    def alias(self):
        if not isinstance(self._token, Identifier):
            raise SQLDecodeError

        return self._token.get_alias()

    @property
    def order(self):
        if not isinstance(self._token, Identifier):
            raise SQLDecodeError

        _ord = self._token.get_ordering()
        if _ord is None:
            raise SQLDecodeError

        return ORDER_BY_MAP[_ord]

    @property
    def left_table(self):
        if not isinstance(self._token, Comparison):
            raise SQLDecodeError

        lhs = SQLToken(self._token.left, self.alias2op)
        return lhs.table

    @property
    def left_column(self):
        if not isinstance(self._token, Comparison):
            raise SQLDecodeError

        lhs = SQLToken(self._token.left, self.alias2op)
        return lhs.column

    @property
    def right_table(self):
        if not isinstance(self._token, Comparison):
            raise SQLDecodeError

        rhs = SQLToken(self._token.right, self.alias2op)
        return rhs.table

    @property
    def right_column(self):
        if not isinstance(self._token, Comparison):
            raise SQLDecodeError

        rhs = SQLToken(self._token.right, self.alias2op)
        return rhs.column

    @property
    def lhs_column(self):
        if not isinstance(self._token, Comparison):
            raise SQLDecodeError

        lhs = SQLToken(self._token.left, self.alias2op)
        return lhs.column

    @property
    def rhs_indexes(self):
        if not self._token.right.ttype == tokens.Name.Placeholder:
            raise SQLDecodeError

        index = self.placeholder_index(self._token.right)
        return index

    @staticmethod
    def placeholder_index(token):
        return int(re.match(r'%\(([0-9]+)\)s', token.value, flags=re.IGNORECASE).group(1))

    def __iter__(self):
        if not isinstance(self._token, Parenthesis):
            raise SQLDecodeError
        tok = self._token[1:-1][0]
        if tok.ttype == tokens.Name.Placeholder:
            yield self.placeholder_index(tok)
            return

        elif tok.match(tokens.Keyword, 'NULL'):
            yield None
            return

        elif isinstance(tok, IdentifierList):
            for aid in tok.get_identifiers():
                if aid.ttype == tokens.Name.Placeholder:
                    yield self.placeholder_index(aid)

                elif aid.match(tokens.Keyword, 'NULL'):
                    yield None

                else:
                    raise SQLDecodeError

        else:
            raise SQLDecodeError


class _Op:
    params: tuple

    def __init__(
            self,
            token_id: int,
            token: Token,
            query: SelectQuery,
            params: tuple = None,
            name='generic'):
        self.lhs: typing.Optional[_Op] = None
        self.rhs: typing.Optional[_Op] = None
        self._token_id = token_id

        if params is not None:
            _Op.params = params
        self.query = query
        self.left_table = query.left_table

        self.token = token
        self.is_negated = False
        self._name = name
        self.precedence = OPERATOR_PRECEDENCE[name]

    def negate(self):
        raise NotImplementedError

    def evaluate(self):
        pass

    def to_mongo(self):
        raise NotImplementedError


class _UnaryOp(_Op):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._op = None

    def negate(self):
        raise NotImplementedError

    def evaluate(self):
        self.rhs.evaluate()

    def to_mongo(self):
        return self.rhs.to_mongo()


class _InNotInLikeOp(_Op):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        identifier = SQLToken(self.token.token_prev(self._token_id)[1], self.query.alias2op)

        if identifier.table == self.left_table:
            self._field = identifier.column
        else:
            self._field = '{}.{}'.format(identifier.table, identifier.column)

    def negate(self):
        raise SQLDecodeError('Negating IN/NOT IN not supported')

    def to_mongo(self):
        raise NotImplementedError


class _InNotInOp(_InNotInLikeOp):

    def _fill_in(self, token):
        self._in = []

        # Check for nested
        if token[1].ttype == tokens.DML:
            self.query.nested_query = NestedInQuery(token, self.query, 0)
            return

        for index in SQLToken(token, self.query.alias2op):
            if index is not None:
                self._in.append(self.params[index])
            else:
                self._in.append(None)

    def negate(self):
        raise SQLDecodeError('Negating IN/NOT IN not supported')

    def to_mongo(self):
        raise NotImplementedError

    def _to_mongo(self, op):
        if self.query.nested_query is not None:
            return {
                '$expr': {
                    op: ['$' + self._field, '$_nested_in']
                }
            }

        else:
            return {self._field: {op: self._in}}


class NotInOp(_InNotInOp):

    def __init__(self, *args, **kwargs):
        super().__init__(name='NOT IN', *args, **kwargs)
        idx, tok = self.token.token_next(self._token_id)
        if not tok.match(tokens.Keyword, 'IN'):
            raise SQLDecodeError
        self._fill_in(self.token.token_next(idx)[1])

    def to_mongo(self):
        op = '$nin' if not self.is_negated else '$in'
        return self._to_mongo(op)

    def negate(self):
        self.is_negated = True


class InOp(_InNotInOp):

    def __init__(self, *args, **kwargs):
        super().__init__(name='IN', *args, **kwargs)
        self._fill_in(self.token.token_next(self._token_id)[1])

    def to_mongo(self):
        op = '$in' if not self.is_negated else '$nin'
        return self._to_mongo(op)

    def negate(self):
        self.is_negated = True


class LikeOp(_InNotInLikeOp):

    def __init__(self, *args, **kwargs):
        super().__init__(name='LIKE', *args, **kwargs)
        self._regex = None
        self._make_regex(self.token.token_next(self._token_id)[1])

    def _make_regex(self, token):
        index = SQLToken.placeholder_index(token)

        to_match =  self.params[index]
        if not isinstance(to_match, str):
            raise SQLDecodeError

        to_match = to_match.replace('%', '.*')
        self._regex = '^'+ to_match + '$'

    def to_mongo(self):
        return {self._field: {'$regex': self._regex}}

class iLikeOp(LikeOp):
    def to_mongo(self):
        return {self._field: {
            '$regex': self._regex,
            '$options': 'i'
        }}


# TODO: Need to do this
class NotOp(_UnaryOp):
    def __init__(self, *args, **kwargs):
        super().__init__(name='NOT', *args, **kwargs)

    def negate(self):
        raise SQLDecodeError

    def evaluate(self):
        self.rhs.negate()
        if isinstance(self.rhs, ParenthesisOp):
            self.rhs.evaluate()
        if self.lhs is not None:
            self.lhs.rhs = self.rhs


class _AndOrOp(_Op):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._acc = []

    def negate(self):
        self.is_negated = True

    def op_type(self):
        raise NotImplementedError

    def evaluate(self):
        if not (self.lhs and self.rhs):
            raise SQLDecodeError

        if isinstance(self.lhs, _AndOrOp):
            if self.op_type() == self.lhs.op_type():
                self._acc = self.lhs._acc + self._acc
            else:
                self._acc.insert(0, self.lhs)

        elif isinstance(self.lhs, ParenthesisOp):
            self.lhs.evaluate()
            self._acc.append(self.lhs)

        elif isinstance(self.lhs, _Op):
            self._acc.append(self.lhs)

        else:
            raise SQLDecodeError

        if isinstance(self.rhs, _AndOrOp):
            if self.op_type() == self.rhs.op_type():
                self._acc.extend(self.rhs._acc)
            else:
                self._acc.append(self.rhs)

        elif isinstance(self.rhs, ParenthesisOp):
            self.rhs.evaluate()
            self._acc.append(self.rhs)

        elif isinstance(self.rhs, _Op):
            self._acc.append(self.rhs)

        else:
            raise SQLDecodeError

        if self.lhs.lhs is not None:
            self.lhs.lhs.rhs = self
        if self.rhs.rhs is not None:
            self.rhs.rhs.lhs = self

    def to_mongo(self):
        if self.op_type() == AndOp:
            oper = '$and'
        else:
            oper = '$or'

        docs = [itm.to_mongo() for itm in self._acc]
        return {oper: docs}


class AndOp(_AndOrOp):

    def __init__(self, *args, **kwargs):
        super().__init__(name='AND', *args, **kwargs)

    def op_type(self):
        if not self.is_negated:
            return AndOp
        else:
            return OrOp


class OrOp(_AndOrOp):

    def __init__(self, *args, **kwargs):
        super().__init__(name='OR', *args, **kwargs)

    def op_type(self):
        if not self.is_negated:
            return OrOp
        else:
            return AndOp


class WhereOp(_Op):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not isinstance(self.token[2], Parenthesis):
            op = ParenthesisOp(0, sqlparse('(' + self.token.value[6:] + ')')[0][0], self.query)
        else:
            op = ParenthesisOp(0, self.token[2], self.query)
        op.evaluate()
        self._op = op

    def negate(self):
        raise NotImplementedError

    def to_mongo(self):
        return self._op.to_mongo()


class ParenthesisOp(_Op):

    def to_mongo(self):
        return self._op.to_mongo()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def link_op():
            if prev_op is not None:
                prev_op.rhs = op
                op.lhs = prev_op

        token = self.token
        self._ops: typing.List[_Op] = []
        self._cmp_ops: typing.List[_Op] = []
        self._op = None

        tok_id, tok = token.token_next(0)
        prev_op: _Op = None
        op: _Op = None
        while tok_id:
            kw = {'token': token, 'token_id': tok_id, 'query': self.query}
            if tok.match(tokens.Keyword, 'AND'):
                op = AndOp(**kw)
                link_op()
                self._op_precedence(op)

            elif tok.match(tokens.Keyword, 'OR'):
                op = OrOp(**kw)
                link_op()
                self._op_precedence(op)

            elif tok.match(tokens.Keyword, 'IN'):
                op = InOp(**kw)
                link_op()
                self._op_precedence(op)

            elif tok.match(tokens.Keyword, 'NOT'):
                _, nxt = token.token_next(tok_id)
                if nxt.match(tokens.Keyword, 'IN'):
                    op = NotInOp(**kw)
                    tok_id, tok = token.token_next(tok_id)
                else:
                    op = NotOp(**kw)
                link_op()
                self._op_precedence(op)

            elif tok.match(tokens.Keyword, 'LIKE'):
                op = LikeOp(**kw)
                link_op()
                self._op_precedence(op)

            elif tok.match(tokens.Keyword, 'iLIKE'):
                op = iLikeOp(**kw)
                link_op()
                self._op_precedence(op)

            elif isinstance(tok, Comparison):
                op = CmpOp(0, tok, self.query)
                self._cmp_ops.append(op)
                link_op()

            elif isinstance(tok, Parenthesis):
                if (tok[1].match(tokens.Name.Placeholder, '.*', regex=True)
                    or tok[1].match(tokens.Keyword, 'Null')
                    or isinstance(tok[1], IdentifierList)
                    or tok[1].ttype == tokens.DML
                ):
                    pass
                else:
                    op = ParenthesisOp(0, tok, self.query)
                    link_op()

            elif tok.match(tokens.Punctuation, ')'):
                if op.lhs is None:
                    if isinstance(op, CmpOp):
                        self._ops.append(op)
                break

            tok_id, tok = token.token_next(tok_id)
            prev_op = op

    def _op_precedence(self, operator: _Op):
        ops = self._ops
        if not ops:
            ops.append(operator)
            return

        for i in range(len(ops)):
            if operator.precedence > ops[i].precedence:
                ops.insert(i, operator)
                break
            else:
                ops.append(operator)

    def evaluate(self):
        if self._op is not None:
            return

        if not self._ops:
            raise SQLDecodeError

        op = None
        while self._ops:
            op = self._ops.pop(0)
            op.evaluate()
        self._op = op

    def negate(self):
        for op in chain(self._ops, self._cmp_ops):
            op.negate()


class CmpOp(_Op):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._identifier = SQLToken(self.token.left, self.query.alias2op)

        if isinstance(self.token.right, Identifier):
            raise SQLDecodeError('Join using WHERE not supported')

        self._operator = OPERATOR_MAP[self.token.token_next(0)[1].value]
        index = re_index(self.token.right.value)

        self._constant = self.params[index] if index is not None else None

    def negate(self):
        self.is_negated = True

    def to_mongo(self):
        if self._identifier.table == self.left_table:
            field = self._identifier.column
        else:
            field = '{}.{}'.format(self._identifier.table, self._identifier.column)

        if not self.is_negated:
            return {field: {self._operator: self._constant}}
        else:
            return {field: {'$not': {self._operator: self._constant}}}

