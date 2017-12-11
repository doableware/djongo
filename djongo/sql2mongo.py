from itertools import chain

from dataclasses import dataclass, field
from pymongo.cursor import Cursor as PymongoCursor
from pymongo.database import Database
from pymongo import MongoClient
from logging import getLogger
import re
import typing
from pymongo import ReturnDocument, ASCENDING, DESCENDING
from sqlparse import parse as sql_parse
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



@dataclass
class WhereQuery:
    nested_op: 'WhereOp' = None
    op: 'WhereOp' = None

@dataclass
class JoinQuery:
    left_table: str = None
    right_table: str = None
    left_column: str = None
    right_column: str = None


class InnerJoinQuery(JoinQuery):
    pass


class OuterJoinQuery(JoinQuery):
    pass


class LimitQuery(typing.NamedTuple):
    limit: int

class OrderQuery(typing.NamedTuple):
    table_column: TableColumnOp
    ord: int

@dataclass
class SelectQuery:
    statement: Statement
    params: typing.Optional[list]

    current_id: int = 0
    current_tok: Token = None
    saved_step: list = field(default_factory=list)

    left_table: typing.Optional[str] = None
    simple_query = True
    alias2op: typing.Dict[str, typing.Any] = field(default_factory=dict)

    selected_ops: typing.List[typing.Any] = field(default_factory=list)
    where: typing.Optional[WhereQuery] = None
    joins: typing.Optional[
        typing.List[
            typing.Union[InnerJoinQuery, OuterJoinQuery]
        ]
    ] = field(default_factory=list)
    order: typing.List[OrderQuery] = field(default_factory=list)
    limit: typing.Optional[LimitQuery] = None


class Parse:

    def __init__(self,
                 client_connection: MongoClient,
                 db_connection: Database,
                 sql: str,
                 params: typing.Optional[list]):
        logger.debug('params: {}'.format(params))

        self._params = params
        self._params_index_count = -1
        self._sql = re.sub(r'%s', self._param_index, sql)
        self.db = db_connection
        self.cli_con = client_connection
        self.last_row_id = None

        self._query = SelectQuery(self._sql, self._params)
        self._parse()

    def result(self):
        return Result(self)

    def _param_index(self, _):
        self._params_index_count += 1
        return '%({})s'.format(self._params_index_count)

    def _parse(self):
        logger.debug('\n sql_command: {}'.format(self._sql))
        statement = sql_parse(self._sql)

        if len(statement) > 1:
            raise SQLDecodeError('Sql: {}'.format(self._sql))

        statement = statement[0]
        sm_type = statement.get_type()

        try:
            handler = self.FUNC_MAP[sm_type]
        except KeyError:
            logger.debug('\n Not implemented {} {}'.format(sm_type, statement))
            raise NotImplementedError('{} command not implemented for SQL {}'.format(sm_type, self._sql))
        else:
            return handler(self, statement)

    def _alter(self, sm):
        next_id, next_tok = sm.token_next(0)
        if next_tok.match(tokens.Keyword, 'TABLE'):
            next_id, next_tok = sm.token_next(next_id)
            if not next_tok:
                logger.debug('Not implemented command not implemented for SQL {}'.format(self._sql))
                return

            table = next(SQLToken.iter_tokens(next_tok)).field

            next_id, next_tok = sm.token_next(next_id)
            if (not next_tok
                or not next_tok.match(tokens.Keyword, 'ADD')
            ):
                logger.debug('Not implemented command not implemented for SQL {}'.format(self._sql))
                return

            next_id, next_tok = sm.token_next(next_id)
            if (not next_tok
                or not next_tok.match(tokens.Keyword, 'CONSTRAINT')
            ):
                logger.debug('Not implemented command not implemented for SQL {}'.format(self._sql))
                return

            next_id, next_tok = sm.token_next(next_id)
            if not isinstance(next_tok, Identifier):
                logger.debug('Not implemented command not implemented for SQL {}'.format(self._sql))
                return

            constraint_name = next_tok.get_name()

            next_id, next_tok = sm.token_next(next_id)
            if not next_tok.match(tokens.Keyword, 'UNIQUE'):
                logger.debug('Not implemented command not implemented for SQL {}'.format(self._sql))
                return

            next_id, next_tok = sm.token_next(next_id)
            if isinstance(next_tok, Parenthesis):
                index = [(field.strip(' "'), 1) for field in next_tok.value.strip('()').split(',')]
                self.db[table].create_index(index, unique=True, name=constraint_name)
            else:
                raise NotImplementedError('Alter command not implemented for SQL {}'.format(self._sql))


    def _create(self, sm):
        next_id, next_tok = sm.token_next(0)
        if next_tok.match(tokens.Keyword, 'TABLE'):
            next_id, next_tok = sm.token_next(next_id)
            table = next(SQLToken.iter_tokens(next_tok)).field
            self.db.create_collection(table)
            logger.debug('Created table {}'.format(table))

            next_id, next_tok = sm.token_next(next_id)
            if isinstance(next_tok, Parenthesis):
                filter = {
                    'name': table
                }
                set = {}
                push = {}
                update = {}

                for col in next_tok.value.strip('()').split(','):
                    field = col[col.find('"') + 1: col.rfind('"')]

                    if col.find('AUTOINCREMENT') != -1:
                        push['auto.field_names'] = field
                        set['auto.seq'] = 0

                    if col.find('PRIMARY KEY') != -1:
                        self.db[table].create_index(field, unique=True, name='__primary_key__')

                    if col.find('UNIQUE') != -1:
                        self.db[table].create_index(field, unique=True)

                if set:
                    update['$set'] = set
                if push:
                    update['$push'] = push
                if update:
                    self.db['__schema__'].update_one(
                        filter=filter,
                        update=update,
                        upsert=True
                    )

        elif next_tok.match(tokens.Keyword, 'DATABASE'):
            pass
        else:
            logger.debug('Not supported {}'.format(sm))

    def _drop(self, sm):
        next_id, next_tok = sm.token_next(0)

        if not next_tok.match(tokens.Keyword, 'DATABASE'):
            raise SQLDecodeError('statement:{}'.format(sm))

        next_id, next_tok = sm.token_next(next_id)
        db_name = next_tok.get_name()
        self.cli_con.drop_database(db_name)

    def _update(self, sm):
        db_con = self.db
        kw = {}
        next_id, next_tok = sm.token_next(0)
        sql_token = next(SQLToken.iter_tokens(next_tok))
        self.left_tbl = collection = sql_token.field

        next_id, next_tok = sm.token_next(next_id)

        if not next_tok.match(tokens.Keyword, 'SET'):
            raise SQLDecodeError('statement:{}'.format(sm))

        upd = {}
        next_id, next_tok = sm.token_next(next_id)
        for cmp_ob in SQLToken.iter_tokens(next_tok):
            if cmp_ob.param_index is not None:
                upd[cmp_ob.field] = self._params[cmp_ob.param_index]
            else:
                upd[cmp_ob.field] = None

        kw['update'] = {'$set': upd}

        next_id, next_tok = sm.token_next(next_id)

        while next_id:
            if isinstance(next_tok, Where):
                where_op = WhereOp(0, next_tok, left_tbl=self.left_tbl, params=self._params)
                kw['filter'] = where_op.to_mongo()
            next_id, next_tok = sm.token_next(next_id)

        result = db_con[collection].update_many(**kw)
        logger.debug('update_many:{} matched:{}'.format(result.modified_count, result.matched_count))
        return None

    def _delete(self, sm):
        db_con = self.db
        kw = {}
        next_id, next_tok = sm.token_next(2)
        sql_token = next(SQLToken.iter_tokens(next_tok))
        collection = sql_token.field
        self.left_tbl = sql_token.field
        next_id, next_tok = sm.token_next(next_id)
        while next_id:
            if isinstance(next_tok, Where):
                where_op = WhereOp(0, next_tok, left_tbl=self.left_tbl, params=self._params)
                kw['filter'] = where_op.to_mongo()
            next_id, next_tok = sm.token_next(next_id)

        result = db_con[collection].delete_many(**kw)
        logger.debug('delete_many: {}'.format(result.deleted_count))

    def _insert(self, sm):
        db_con = self.db
        insert = {}
        nextid, nexttok = sm.token_next(2)
        if isinstance(nexttok, Identifier):
            collection = nexttok.get_name()
            auto = db_con['__schema__'].find_one_and_update(
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
            raise SQLDecodeError('statement: {}'.format(sm))

        nextid, nexttok = sm.token_next(nextid)

        for sql_ob in SQLToken.iter_tokens(nexttok):
            insert[sql_ob.field] = self._params.pop(0)

        if self._params:
            raise SQLDecodeError('unexpected params {}'.format(self._params))

        result = db_con[collection].insert_one(insert)
        if not auto_field_id:
            auto_field_id = str(result.inserted_id)

        self.last_row_id = auto_field_id
        logger.debug('insert id {}'.format(result.inserted_id))
        return None

    def _select(self, sm):

        query = SelectQuery(sm, self._params)
        current_step = SelectStep(query)
        current_step.run_steps(StartSelectStep(query), StopSelectStep)

        while not isinstance(current_step, StopSelectStep):
            current_step.parse()
            current_step = current_step.next_step()

        next_id, next_tok = sm.token_next(0)
        if next_tok.value == '*':
            self.proj.no_id = True

        elif isinstance(next_tok, Identifier) and isinstance(next_tok.tokens[0], Parenthesis):
            self.proj.return_const = int(next_tok.tokens[0].tokens[1].value)

        elif (isinstance(next_tok, Identifier)
              and isinstance(next_tok.tokens[0], Function)
              and next_tok.tokens[0].token_first().value == 'COUNT'):
            self.proj.return_count = True

        elif next_tok.match(tokens.Keyword, 'DISTINCT'):
            self.distinct = True
            next_id, next_tok = sm.token_next(next_id)
            for sql in SQLToken.iter_tokens(next_tok):
                self.proj.coll_fields.append(TableColumnOp(sql.coll, sql.field))

            if len(self.proj.coll_fields) > 1:
                raise SQLDecodeError('Distinct for more than 1 field not supported yet')

        else:
            for sql in SQLToken.iter_tokens(next_tok):
                self.proj.coll_fields.append(TableColumnOp(sql.coll, sql.field))

        next_id, next_tok = sm.token_next(next_id)

        if not next_tok.match(tokens.Keyword, 'FROM'):
            raise SQLDecodeError('statement: {}'.format(sm))

        next_id, next_tok = sm.token_next(next_id)
        sql = next(SQLToken.iter_tokens(next_tok))

        self.left_tbl = sql.field

        next_id, next_tok = sm.token_next(next_id)

        while next_id:
            if isinstance(next_tok, Where):
                where_op = WhereOp(
                    token_id=0,
                    token=next_tok,
                    left_tbl=self.left_tbl,
                    params=self._params
                )
                self.filter = where_op.to_mongo()

            elif next_tok.match(tokens.Keyword, 'LIMIT'):
                next_id, next_tok = sm.token_next(next_id)
                self.limit = int(next_tok.value)

            elif (next_tok.match(tokens.Keyword, 'INNER JOIN')
                  or next_tok.match(tokens.Keyword, 'LEFT OUTER JOIN')):
                if next_tok.match(tokens.Keyword, 'INNER JOIN'):
                    join = InnerJoinQuery()
                else:
                    join = OuterJoinQuery()

                next_id, next_tok = sm.token_next(next_id)
                sql = next(SQLToken.iter_tokens(next_tok))
                right_tb = join.right_table = sql.field

                next_id, next_tok = sm.token_next(next_id)
                if not next_tok.match(tokens.Keyword, 'ON'):
                    raise SQLDecodeError('statement: {}'.format(sm))

                next_id, next_tok = sm.token_next(next_id)
                join_token = next(SQLToken.iter_tokens(next_tok))
                if right_tb == join_token.other_coll:
                    join.left_column = join_token.field
                    join.right_column = join_token.other_field
                    join.left_table = join_token.coll
                else:
                    join.left_column = join_token.other_field
                    join.right_column = join_token.field
                    join.left_table = join_token.other_coll

                self.joins.append(join)

            elif next_tok.match(tokens.Keyword, 'ORDER'):
                next_id, next_tok = sm.token_next(next_id)
                if not next_tok.match(tokens.Keyword, 'BY'):
                    raise SQLDecodeError('statement: {}'.format(sm))

                next_id, next_tok = sm.token_next(next_id)
                for order, sql in SQLToken.iter_tokens(next_tok):
                    self.sort.append(
                        OrderQuery(TableColumnOp(sql.coll, sql.field),
                                   ORDER_BY_MAP[order]))

            else:
                raise SQLDecodeError('statement: {}'.format(sm))

            next_id, next_tok = sm.token_next(next_id)

    FUNC_MAP = {
        'SELECT': _select,
        'UPDATE': _update,
        'INSERT': _insert,
        'DELETE': _delete,
        'CREATE': _create,
        'DROP': _drop,
        'ALTER': _alter
    }


class Step:
    token_to_step_map = None
    keyword_to_step_map = None

    def __init__(self, query: SelectQuery):
        self._query = query

    @staticmethod
    def run_steps(start_step, stop_step_class):
        current_step = start_step

        while not isinstance(current_step, stop_step_class):
            current_step.parse()
            current_step = current_step.next_step()

    def save_step(self):
        q = self._query
        q.saved_step.append((
            q.current_id,
            q.current_tok,
            q.statement))
        q.statement: Token = q.current_tok
        q.current_tok = q.statement[0]
        q.current_id = 0

    def restore_step(self):
        q = self._query
        (q.current_id,
         q.current_tok,
         q.statement) = q.saved_step.pop()

    def token_to_step(self, token: Token):
        q = self._query
        try:
            return self.token_to_step_map[type(token)](q)
        except KeyError:
            raise SQLDecodeError(f'Not Implemented: {q.statement}')

    def keyword_to_step(self):
        q = self._query
        current_tok = q.current_tok
        found_step = None
        for keyword, step in self.keyword_to_step_map:
            if current_tok.match(tokens.Keyword, keyword):
                found_step = step
                break
        else:
            raise SQLDecodeError(f'Not Implemented: {q.statement}')
        return found_step(q)

    def advance(self, by=1):
        q = self._query
        for _ in range(by):
            q.current_id, q.current_tok = q.statement.token_next(q.current_id)

    def parse(self):
        raise NotImplementedError

    def next_step(self):
        raise NotImplementedError


class IdentifierStep(Step):

    def parse(self):
        self.run_steps(StartIdentifierStep(self._query), StopIdentifierStep)

    def next_step(self):
        return StopColumnSelectStep(self._query)

class StartIdentifierStep(Step):

    def parse(self):
        q = self._query
        if isinstance(q.current_tok, Function):
            if q.current_tok[0].value == 'COUNT':
                self.save_step()
                self.run_steps(CountStep(q), StopIdentifierStep)
                self.restore_step()
        else:
            # Normal identifier
            sql_tok = SQLLToken(q.statement)
            q.selected_ops.append(TableColumnOp(sql_tok.table, sql_tok.column))

        alias = q.statement.get_alias()
        op = q.selected_ops[-1]
        op.alias_name = alias
        q.alias2op[alias] = op

    def next_step(self):
        return StopIdentifierStep(self._query)
        self.advance()
        q = self._query
        if q.current_tok is None:
            return StopIdentifierStep(q)
        # An alias exists
        return AliasIdentifierStep(q)


class AliasIdentifierStep(Step):

    def parse(self):
        q = self._query
        if not q.current_tok.match(tokens.Keyword, 'AS'):
            raise SQLDecodeError
        self.advance()
        alias = q.statement.get_alias()
        op = q.selected_ops[-1]
        op.alias_name = alias
        q.alias2op[alias] = op

    def next_step(self):
        return StopIdentifierStep(self._query)

class StopIdentifierStep(Step):
    pass

class CountStep(Step):

    def parse(self):
        self.run_steps(StartCountStep(self._query), StopCountStep)

    def next_step(self):
        return StopIdentifierStep(self._query)

class StartCountStep(CountStep):
    def parse(self):
        q = self._query
        self.advance()
        if not isinstance(q.current_tok, Parenthesis):
            raise SQLDecodeError

        self.save_step()
        self.advance()

        if q.current_tok.match(tokens.Wildcard, '*'):
            op = CountWildcardFunc()

        elif isinstance(q.current_tok, Identifier):
            sql_tok = SQLLToken(q.current_tok)
            op = CountFunc(sql_tok.table, sql_tok.column)
        elif q.current_tok.match(tokens.Keyword, 'DISTINCT'):
            q.simple_query = False
            pass
        self.advance(2)
        q.selected_ops.append(op)

        if q.current_tok is not None:
            raise SQLDecodeError
        self.restore_step()

    def next_step(self):
        return StopCountStep(self._query)

class StopCountStep(CountStep):
    pass

class SelectStep(Step):
    pass


class StartSelectStep(SelectStep):

    def parse(self):
        q = self._query
        q.current_id, q.current_tok = q.statement.token_next(0)

    def next_step(self):
        return ColumnSelectStep(self._query)


class StopSelectStep(SelectStep):
    pass

class ColumnSelectStep(SelectStep):

    def parse(self):
        q = self._query
        self.save_step()
        self.run_steps(StartColumnSelectStep(q), StopColumnSelectStep)
        self.restore_step()

    def next_step(self):
        q = self._query
        self.advance()
        if not q.current_tok.match(tokens.Keyword, 'FROM'):
            raise SQLDecodeError

        return FromSelectStep(q)

class StartColumnSelectStep(ColumnSelectStep):
    token_to_step_map = None

    def __init__(self, q):
        super().__init__(q)

        if StartColumnSelectStep.token_to_step_map is None:
            StartColumnSelectStep.token_to_step_map = {
                Token: TokenColumnSelectStep,
                Identifier: IdentifierStep,
                IdentifierList: IdentifierListColumnSelectStep
            }

    def parse(self):
        q = self._query

        if isinstance(q.statement, Parenthesis):
            q.statement = q.statement[0]
            q.current_id = 0
            q.current_tok = q.statement[0]

    def next_step(self):
        return self.token_to_step(self._query.statement)

class StopColumnSelectStep(ColumnSelectStep):
    pass

class TokenColumnSelectStep(ColumnSelectStep):

    def parse(self):
        q = self._query
        if q.current_tok.match(tokens.Keyword, 'COUNT'):
            self.save_step()
            self.run_steps(StartCountStep(self._query), StopCountStep)
            self.restore_step()
        elif q.current_tok.match(tokens.Keyword, 'DISTINCT'):
            q.selected_ops
            self.advance()

    def next_step(self):
        StopColumnSelectStep(self._query)

class IdentifierColumnSelectStep(ColumnSelectStep):

    def parse(self):
        pass


class IdentifierListColumnSelectStep(ColumnSelectStep):

    def parse(self):
        self.run_steps(StartIdentifierListColumnSelectStep(self._query), StopIdentifierListColumnSelectStep)

    def next_step(self):
        return StopColumnSelectStep(self._query)

class StartIdentifierListColumnSelectStep(IdentifierListColumnSelectStep):

    def parse(self):
        self.save_step()
        self.run_steps(IdentifierStep(self._query), StopColumnSelectStep)
        self.restore_step()

    def next_step(self):
        self.advance(2)
        if self._query.current_tok is None:
            return StopIdentifierListColumnSelectStep(self._query)
        return StartIdentifierListColumnSelectStep(self._query)

class StopIdentifierListColumnSelectStep(IdentifierListColumnSelectStep):
    pass


class FromSelectStep(SelectStep):
    pass


class JoinSelectStep(SelectStep):
    pass

class GroupbySelectStep(SelectStep):
    pass

class HavingSelectStep(SelectStep):
    pass

class WhereSelectStep(SelectStep):
    pass

class LimitSelectStep(SelectStep):
    pass

class SortSelectStep(SelectStep):
    pass

class SkipSelectStep(SelectStep):
    pass




class Projection:

    def __init__(self):
        self.return_const: typing.Any = None
        self.return_count = False
        self.no_id = True
        self.coll_fields: typing.List[TableColumnOp] = []


class Result:

    def __init__(self, parsed_sql: Parse):
        self._parsed_sql = parsed_sql
        self._cursor = None
        self._returned_count = 0
        self._count_returned = False
        self._count: int = None

    def _get_cursor(self):
        p_sql = self._parsed_sql
        if p_sql.joins:
            # Do aggregation lookup
            pipeline = []
            for i, join in enumerate(p_sql.joins):
                if join.left_table == p_sql.left_tbl:
                    local_field = join.local_column
                else:
                    local_field = '{}.{}'.format(join.left_table, join.local_column)

                lookup = {
                    '$lookup': {
                        'from': join.right_table,
                        'localField': local_field,
                        'foreignField': join.foreign_field,
                        'as': join.right_table
                    }
                }

                if isinstance(join, InnerJoinQuery):
                    if i == 0:
                        if join.left_table != p_sql.left_tbl:
                            raise SQLDecodeError

                        pipeline.append({
                            '$match': {
                                join.left_column: {
                                    '$ne': None,
                                    '$exists': True
                                }
                            }
                        })

                    pipeline.extend([
                        lookup,
                        {
                            '$unwind': '$'+join.right_table
                        }
                    ])
                else:
                    if i == 0:
                        if join.left_table != p_sql.left_tbl:
                            raise SQLDecodeError

                    pipeline.extend([
                        lookup,
                        {
                            '$unwind': {
                                'path': '$'+join.right_table,
                                'preserveNullAndEmptyArrays': True
                            }
                        }
                    ])

            if p_sql.filter:
                pipeline.append({
                    '$match': p_sql.filter
                })

            if p_sql.distinct:
                pipeline.extend([
                    {
                        '$group': {
                            '_id': '$'+p_sql.proj.coll_fields[0].field
                        }
                    },
                    {
                        '$project': {
                            p_sql.proj.coll_fields[0].field: '$_id'
                        }
                    }
                ])

            if p_sql.sort:
                sort = OrderedDict()
                for s in p_sql.sort:
                    if s.coll_field.coll == p_sql.left_tbl:
                        sort[s.coll_field.field] = s.ord
                    else:
                        sort[s.coll_field.coll + '.' + s.coll_field.field] = s.ord

                pipeline.append({
                    '$sort': sort
                })

            if p_sql.limit:
                pipeline.append({
                    '$limit': p_sql.limit
                })

            if p_sql.proj.coll_fields:
                proj = {}
                for fld in p_sql.proj.coll_fields:
                    if fld.coll == p_sql.left_tbl:
                        proj[fld.field] = True
                    else:
                        proj[fld.coll + '.' + fld.field] = True

                pipeline.append({'$project': proj})

            return p_sql.db[p_sql.left_tbl].aggregate(pipeline)

        else:
            query_args = {}
            if p_sql.proj.coll_fields:
                query_args['projection'] = [f.field for f in p_sql.proj.coll_fields]

            if p_sql.filter:
                query_args['filter'] = p_sql.filter

            if p_sql.limit is not None:
                query_args['limit'] = p_sql.limit

            if p_sql.sort:
                query_args['sort'] = [(s.coll_field.field, s.ord) for s in p_sql.sort]

            pym_cur = p_sql.db[p_sql.left_tbl].find(**query_args)
            if p_sql.distinct:
                pym_cur = pym_cur.distinct(p_sql.proj.coll_fields[0].field)

            return pym_cur

    def count(self):
        if self._count is not None:
            return self._count

        if self._cursor is None:
            self._cursor = self._get_cursor()

        if isinstance(self._cursor, PymongoCursor):
            self._count = self._cursor.count()
        else:
            self._count = len(list(self._cursor))

        return self._count

    def __iter__(self):
        return self

    def next(self):
        p_sql = self._parsed_sql
        if p_sql.proj.return_const is not None:
            if self._returned_count < self.count():
                self._returned_count += 1
                return p_sql.proj.return_const,
            else:
                raise StopIteration

        if p_sql.proj.return_count:
            if not self._count_returned:
                self._count_returned = True
                return self.count(),
            else:
                raise StopIteration

        if self._cursor is None:
            self._cursor = self._get_cursor()

        cur = self._cursor
        doc = cur.next()
        if isinstance(cur, PymongoCursor):
            doc.pop('_id')
            if len(doc) == len(p_sql.proj.coll_fields):
                return tuple(doc.values())

        ret = []
        for coll_field in p_sql.proj.coll_fields:
            if coll_field.coll == p_sql.left_tbl:
                try:
                    ret.append(doc[coll_field.field])
                except KeyError:
                    ret.append(None)
            else:
                try:
                    ret.append(doc[coll_field.coll][coll_field.field])
                except KeyError:
                    ret.append(None)
        return ret

    __next__ = next

    def close(self):
        if self._cursor:
            self._cursor.close()


class SQLLToken:

    def __init__(self, token: Token):
        self._token = token

    @property
    def table(self):
        if not isinstance(self._token, Identifier):
            raise SQLDecodeError

        return self._token.get_parent_name()

    @property
    def column(self):
        if not isinstance(self._token, Identifier):
            raise SQLDecodeError

        return self._token.get_real_name()

    @property
    def left_table(self):
        if not isinstance(self._token, Comparison):
            raise SQLDecodeError

        lhs = SQLLToken(self._token.left)
        return lhs.table

    @property
    def left_column(self):
        if not isinstance(self._token, Comparison):
            raise SQLDecodeError

        lhs = SQLLToken(self._token.left)
        return lhs.column

    @property
    def right_table(self):
        if not isinstance(self._token, Comparison):
            raise SQLDecodeError

        rhs = SQLLToken(self._token.right)
        return rhs.table

    @property
    def right_column(self):
        if not isinstance(self._token, Comparison):
            raise SQLDecodeError

        rhs = SQLLToken(self._token.right)
        return rhs.column

    def __iter__(self):
        if not isinstance(self._token, IdentifierList):
            raise SQLDecodeError

class SQLToken:
    def __init__(self, field, coll=None):
        self.field = field
        self.coll = coll

    @classmethod
    def iter_tokens(cls, token):
        if isinstance(token, Identifier):
            tok_first = token.token_first()
            if isinstance(tok_first, Identifier):
                yield token.get_ordering(), cls(tok_first.get_name(), tok_first.get_parent_name())
            else:
                yield cls(token.get_name(), token.get_parent_name())

        elif isinstance(token, IdentifierList):
            for iden in token.get_identifiers():
                yield from SQLToken.iter_tokens(iden)

        elif isinstance(token, Comparison):
            lhs = next(SQLToken.iter_tokens(token.left))
            if isinstance(token.right, Identifier):
                rhs = next(SQLToken.iter_tokens(token.right))
                yield JoinToken(
                    other_field=rhs.field,
                    other_coll=rhs.coll,
                    field=lhs.field,
                    coll=lhs.coll)

            else:
                if token.token_next(0)[1].value != '=':
                    raise SQLDecodeError

                yield EqToken(**vars(lhs), param_index=re_index(token.right.value))

        elif isinstance(token, Parenthesis):
            next_id, next_tok = token.token_next(0)
            while next_tok.value != ')':
                yield from SQLToken.iter_tokens(next_tok)
                next_id, next_tok = token.token_next(next_id)

        elif token.match(tokens.Name.Placeholder, '.*', regex=True):
            index = int(re.match(r'%\(([0-9]+)\)s', token.value, flags=re.IGNORECASE).group(1))
            yield index

        elif token.match(tokens.Keyword, 'NULL'):
            yield None
        else:
            raise SQLDecodeError

    def to_mongo(self):
        raise SQLDecodeError


class EqToken(SQLToken):
    def __init__(self, param_index, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.param_index = param_index


class JoinToken(SQLToken):
    def __init__(self, other_field, other_coll, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.other_field = other_field
        self.other_coll = other_coll


class _Op:
    params: tuple
    left_tbl: str

    def __init__(
            self,
            token_id: int,
            token: Token,
            left_tbl: str=None,
            params: tuple=None,
            name='generic'):
        self.lhs: typing.Optional[_Op] = None
        self.rhs: typing.Optional[_Op] = None
        self._token_id = token_id

        if params is not None:
            _Op.params = params
        if left_tbl is not None:
            _Op.left_tbl = left_tbl

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


class _InNotInOp(_Op):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        identifier = next(SQLToken.iter_tokens(self.token.token_prev(self._token_id)[1]))
        if identifier.coll:
            if identifier.coll == self.left_tbl:
                self._field = identifier.field
            else:
                self._field = '{}.{}'.format(identifier.coll, identifier.field)
        else:
            self._field = identifier.field

    def _fill_in(self, token):
        self._in = []
        for index in SQLToken.iter_tokens(token):
            if index is not None:
                self._in.append(self.params[index])
            else:
                self._in.append(None)

    def negate(self):
        raise SQLDecodeError('Negating IN/NOT IN not supported')

    def to_mongo(self):
        raise NotImplementedError


class NotInOp(_InNotInOp):

    def __init__(self, *args, **kwargs):
        super().__init__(name='NOT IN', *args, **kwargs)
        idx, tok = self.token.token_next(self._token_id)
        if not tok.match(tokens.Keyword, 'IN'):
            raise SQLDecodeError
        self._fill_in(self.token.token_next(idx)[1])

    def to_mongo(self):
        op = '$nin' if not self.is_negated else '$in'
        return {self._field: {op: self._in}}

    def negate(self):
        self.is_negated = True

class InOp(_InNotInOp):

    def __init__(self, *args, **kwargs):
        super().__init__(name='IN', *args, **kwargs)
        self._fill_in(self.token.token_next(self._token_id)[1])

    def to_mongo(self):
        op = '$in' if not self.is_negated else '$nin'
        return {self._field: {op: self._in}}

    def negate(self):
        self.is_negated = True


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
            op = ParenthesisOp(0, sql_parse('('+self.token.value[6:]+')')[0][0])
        else:
            op = ParenthesisOp(0, self.token[2])
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

        next_id, next_tok = token.token_next(0)
        prev_op: _Op = None
        op: _Op = None
        while next_id:
            kw = {'token': token, 'token_id': next_id}
            if next_tok.match(tokens.Keyword, 'AND'):
                op = AndOp(**kw)
                link_op()
                self._op_precedence(op)

            elif next_tok.match(tokens.Keyword, 'OR'):
                op = OrOp(**kw)
                link_op()
                self._op_precedence(op)

            elif next_tok.match(tokens.Keyword, 'IN'):
                op = InOp(**kw)
                link_op()
                self._op_precedence(op)

            elif next_tok.match(tokens.Keyword, 'NOT'):
                _, nxt = token.token_next(next_id)
                if nxt.match(tokens.Keyword, 'IN'):
                    op = NotInOp(**kw)
                    next_id, next_tok = token.token_next(next_id)
                else:
                    op = NotOp(**kw)
                link_op()
                self._op_precedence(op)

            elif isinstance(next_tok, Comparison):
                op = CmpOp(0, next_tok)
                self._cmp_ops.append(op)
                link_op()

            elif isinstance(next_tok, Parenthesis):
                if next_tok[1].match(tokens.Name.Placeholder, '.*', regex=True):
                    pass
                elif next_tok[1].match(tokens.Keyword, 'Null'):
                    pass
                elif isinstance(next_tok[1], IdentifierList):
                    pass
                else:
                    op = ParenthesisOp(0, next_tok)
                    link_op()

            elif next_tok.match(tokens.Punctuation, ')'):
                if op.lhs is None:
                    if isinstance(op, CmpOp):
                        self._ops.append(op)
                break

            next_id, next_tok = token.token_next(next_id)
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

        self._identifier = next(SQLToken.iter_tokens(self.token.left))

        if isinstance(self.token.right, Identifier):
            raise SQLDecodeError('Join using WHERE not supported')

        self._operator = OPERATOR_MAP[self.token.token_next(0)[1].value]
        index = re_index(self.token.right.value)

        self._constant = self.params[index] if index is not None else None

    def negate(self):
        self.is_negated = True

    def to_mongo(self):
        if self._identifier.coll == self.left_tbl:
            field = self._identifier.field
        else:
            field = '{}.{}'.format(self._identifier.coll, self._identifier.field)

        if not self.is_negated:
            return {field: {self._operator: self._constant}}
        else:
            return {field: {'$not': {self._operator: self._constant}}}