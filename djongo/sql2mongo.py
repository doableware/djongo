from pymongo.cursor import Cursor as PymongoCursor
from logging import getLogger
import re
import typing
from pymongo import ReturnDocument, ASCENDING, DESCENDING
from sqlparse import parse as sql_parse
from sqlparse import tokens
from sqlparse.sql import (
    IdentifierList, Identifier, Parenthesis,
    Where, Comparison, Function, Token
)
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
    'IN': 1,
    'NOT': 2,
    'AND': 3,
    'OR': 4,
    'generic': 50
}

ORDER_BY_MAP = {
    'ASC': ASCENDING,
    'DESC': DESCENDING
}


class SQLDecodeError(ValueError):
    pass


class CollField(typing.NamedTuple):
    coll: str
    field: str


class SortOrder(typing.NamedTuple):
    coll_field: CollField
    ord: int

class Join:

    def __init__(self):
        self.left_table: str = None
        self.right_table: str = None
        self.local_field: str = None
        self.foreign_field: str = None


class InnerJoin(Join):
    pass


class OuterJoin(Join):
    pass


class Projection:

    def __init__(self):
        self.return_const: typing.Any = None
        self.return_count = False
        self.no_id = True
        self.coll_fields: typing.List[CollField] = []


class Parse:

    def __init__(self, connection, sql, params):
        logger.debug('params: {}'.format(params))

        self._params = params
        self._p_index_count = -1
        self._sql = re.sub(r'%s', self._param_index, sql)
        self.db = connection
        self.left_tbl: str = None

        self.last_row_id = None

        self.proj = Projection()
        self.filter: dict = None
        self.sort: typing.List[SortOrder] = []
        self.limit: int = None
        self.joins: typing.List[typing.Union[InnerJoin, OuterJoin]] = []

        self._parse()

    def result(self):
        return Result(self)

    def _param_index(self, _):
        self._p_index_count += 1
        return '%({})s'.format(self._p_index_count)

    def _parse(self):
        logger.debug('\n mongo_cur: {}'.format(self._sql))
        statement = sql_parse(self._sql)

        if len(statement) > 1:
            raise SQLDecodeError('Sql: {}'.format(self._sql))

        statement = statement[0]
        sm_type = statement.get_type()

        # Some of these commands can be ignored, some need to be implemented.
        if sm_type in ('CREATE', 'ALTER', 'DROP'):
            return None

        try:
            return self.FUNC_MAP[sm_type](self, statement)
        except KeyError:
            logger.debug('\n Not implemented {} {}'.format(sm_type, statement))
            raise NotImplementedError('{} command not implemented for SQL {}'.format(sm_type, self._sql))

    @staticmethod
    def _iter_tok(tok):
        nextid, nexttok = tok.token_next(0)
        while nextid:
            yield nexttok
            nextid, nexttok = tok.token_next(nextid)

    def _update(self, sm):
        db_con = self.db
        kw = {}
        next_id, next_tok = sm.token_next(0)
        sql_ob = next(SQLToken.token_2_obj(next_tok, self.left_tbl, self._params))
        collection = sql_ob.field
        self.left_tbl = sql_ob.field

        next_id, next_tok = sm.token_next(next_id)

        if not next_tok.match(tokens.Keyword, 'SET'):
            raise SQLDecodeError('statement:{}'.format(sm))

        upd = {}
        next_id, next_tok = sm.token_next(next_id)
        for cmp_ob in SQLToken.token_2_obj(next_tok, left_tbl=self.left_tbl, params=self._params):
            upd[cmp_ob.field] = cmp_ob.rhs_obj
        kw['update'] = {'$set': upd}

        next_id, next_tok = sm.token_next(next_id)

        while next_id:
            if isinstance(next_tok, Where):
                where_op = Op.token_2_op(next_tok, left_tbl=self.left_tbl, params=self._params)
                kw['filter'] = where_op.to_mongo()
            next_id, next_tok = sm.token_next(next_id)

        result = db_con[collection].update_many(**kw)
        logger.debug('update_many:{} matched:{}'.format(result.modified_count, result.matched_count))
        return None

    def _delete(self, sm):
        db_con = self.db
        kw = {}
        next_id, next_tok = sm.token_next(2)
        sql_ob = next(SQLToken.token_2_obj(next_tok, left_tbl=self.left_tbl, params=self._params))
        collection = sql_ob.field
        self.left_tbl = sql_ob.field
        next_id, next_tok = sm.token_next(next_id)
        while next_id:
            if isinstance(next_tok, Where):
                where_op = Op.token_2_op(next_tok, left_tbl=self.left_tbl, params=self._params)
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
                {'name': collection},
                {'$inc': {'auto.seq': 1}},
                return_document=ReturnDocument.AFTER
            )

            if auto:
                auto_field_name = auto['auto']['field_name']
                auto_field_id = auto['auto']['seq']
                insert[auto_field_name] = auto_field_id
            else:
                auto_field_id = None
        else:
            raise SQLDecodeError('statement: {}'.format(sm))

        nextid, nexttok = sm.token_next(nextid)

        for sql_ob in SQLToken.token_2_obj(nexttok, left_tbl=self.left_tbl, params=self._params):
            insert[sql_ob.field] = self._params.pop(0)

        if self._params:
            raise SQLDecodeError('unexpected params {}'.format(self._params))

        result = db_con[collection].insert_one(insert)
        if not auto_field_id:
            auto_field_id = str(result.inserted_id)

        self.last_row_id = auto_field_id
        logger.debug('insert id {}'.format(result.inserted_id))
        return None

    def _find(self, sm):

        next_id, next_tok = sm.token_next(0)
        if next_tok.value == '*':
            self.proj.no_id = True

        elif isinstance(next_tok, Identifier) and isinstance(next_tok.tokens[0], Parenthesis):
            self.proj.return_const = int(next_tok.tokens[0].tokens[1].value)

        elif (isinstance(next_tok, Identifier)
              and isinstance(next_tok.tokens[0], Function)
              and next_tok.tokens[0].token_first().value == 'COUNT'):
            self.proj.return_count = True

        else:
            for sql in SQLToken.token_2_obj(next_tok, self.left_tbl, self._params):
                self.proj.coll_fields.append(CollField(sql.coll, sql.field))

        next_id, next_tok = sm.token_next(next_id)

        if not next_tok.match(tokens.Keyword, 'FROM'):
            raise SQLDecodeError('statement: {}'.format(sm))

        next_id, next_tok = sm.token_next(next_id)
        sql = next(SQLToken.token_2_obj(next_tok, self.left_tbl, self._params))

        self.left_tbl = sql.field

        next_id, next_tok = sm.token_next(next_id)

        while next_id:
            if isinstance(next_tok, Where):
                where_op = Op.token_2_op(next_tok, left_tbl=self.left_tbl, params=self._params)
                self.filter = where_op.to_mongo()

            elif next_tok.match(tokens.Keyword, 'LIMIT'):
                next_id, next_tok = sm.token_next(next_id)
                self.limit = int(next_tok.value)

            elif (next_tok.match(tokens.Keyword, 'INNER JOIN')
                  or next_tok.match(tokens.Keyword, 'LEFT OUTER JOIN')):
                if next_tok.match(tokens.Keyword, 'INNER JOIN'):
                    join = InnerJoin()
                else:
                    join = OuterJoin()

                next_id, next_tok = sm.token_next(next_id)
                sql = next(SQLToken.token_2_obj(next_tok, self.left_tbl, self._params))
                right_tb = join.right_table = sql.field

                next_id, next_tok = sm.token_next(next_id)
                if not next_tok.match(tokens.Keyword, 'ON'):
                    raise SQLDecodeError('statement: {}'.format(sm))

                next_id, next_tok = sm.token_next(next_id)
                join_ob = next(SQLToken.token_2_obj(next_tok, self.left_tbl, self._params))
                if right_tb == join_ob.other_coll:
                    join.local_field = join_ob.field
                    join.foreign_field = join_ob.other_field
                    join.left_table = join_ob.coll
                else:
                    join.local_field = join_ob.other_field
                    join.foreign_field = join_ob.field
                    join.left_table = join_ob.other_coll

                self.joins.append(join)

            elif next_tok.match(tokens.Keyword, 'ORDER'):
                next_id, next_tok = sm.token_next(next_id)
                if not next_tok.match(tokens.Keyword, 'BY'):
                    raise SQLDecodeError('statement: {}'.format(sm))

                next_id, next_tok = sm.token_next(next_id)
                for order, sql in SQLToken.token_2_obj(next_tok, self.left_tbl, self._params):
                    self.sort.append(
                        SortOrder(CollField(sql.coll, sql.field),
                                  ORDER_BY_MAP[order]))

            else:
                raise SQLDecodeError('statement: {}'.format(sm))

            next_id, next_tok = sm.token_next(next_id)

    FUNC_MAP = {
        'SELECT': _find,
        'UPDATE': _update,
        'INSERT': _insert,
        'DELETE': _delete
    }


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
                    local_field = join.local_field
                else:
                    local_field = '{}.{}'.format(join.left_table, join.local_field)

                lookup = {
                    '$lookup': {
                        'from': join.right_table,
                        'localField': local_field,
                        'foreignField': join.foreign_field,
                        'as': join.right_table
                    }
                }

                if isinstance(join, InnerJoin):
                    if i == 0:
                        if join.left_table != p_sql.left_tbl:
                            raise SQLDecodeError

                        pipeline.append({
                            '$match': {
                                join.local_field: {
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

            if p_sql.filter:
                pipeline.append({
                    '$match': p_sql.filter
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
                query_args['sort'] = [(s.coll_field.field , s.ord) for s in p_sql.sort]

            return p_sql.db[p_sql.left_tbl].find(**query_args)

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
            return tuple(doc.values())
        else:
            ret = []
            for coll_field in p_sql.proj.coll_fields:
                if coll_field.coll == p_sql.left_tbl:
                    ret.append(doc[coll_field.field])
                else:
                    ret.append(doc[coll_field.coll][coll_field.field])
            return ret

    __next__ = next

    def close(self):
        if self._cursor:
            self._cursor.close()

class SQLToken:
    def __init__(self, field, coll=None, left_tbl=None):
        self.field = field
        self.coll = coll
        self.left_tbl = left_tbl

    @classmethod
    def token_2_obj(cls, token, left_tbl, params):
        if isinstance(token, Identifier):
            tok_first = token.token_first()
            if isinstance(tok_first, Identifier):
                yield token.get_ordering(), cls(tok_first.get_name(), tok_first.get_parent_name(), left_tbl)
            else:
                yield cls(token.get_name(), token.get_parent_name(), left_tbl)

        elif isinstance(token, IdentifierList):
            for iden in token.get_identifiers():
                yield from SQLToken.token_2_obj(iden, left_tbl, params)

        elif isinstance(token, Comparison):
            lhs = next(SQLToken.token_2_obj(token.left, left_tbl, params))
            if isinstance(token.right, Identifier):
                rhs = next(SQLToken.token_2_obj(token.right, left_tbl, params))
                yield JoinToken(
                    other_field=rhs.field,
                    other_coll=rhs.coll,
                    field=lhs.field,
                    coll=lhs.coll,
                    left_tbl=left_tbl)

            else:
                op = OPERATOR_MAP[token.token_next(0)[1].value]
                index = int(re.match(r'%\(([0-9]+)\)s', token.right.value, flags=re.IGNORECASE).group(1))
                yield CmpToken(**vars(lhs), operator=op, rhs_obj=params[index])

        elif isinstance(token, Parenthesis):
            next_id, next_tok = token.token_next(0)
            while next_tok.value != ')':
                yield from SQLToken.token_2_obj(next_tok, left_tbl, params)
                next_id, next_tok = token.token_next(next_id)

        elif token.match(tokens.Name.Placeholder, '.*', regex=True):
            index = int(re.match(r'%\(([0-9]+)\)s', token.value, flags=re.IGNORECASE).group(1))
            yield params[index]

        else:
            raise SQLDecodeError

    def to_mongo(self):
        raise SQLDecodeError


class JoinToken(SQLToken):
    def __init__(self, other_field, other_coll, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.other_field = other_field
        self.other_coll = other_coll


class CmpToken(SQLToken):
    def __init__(self, operator, rhs_obj, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.operator = operator
        self.rhs_obj = rhs_obj
        self.is_not = False

    def to_mongo(self):
        if self.coll == self.left_tbl:
            field = self.field
        else:
            field = '{}.{}'.format(self.coll, self.field)

        if not self.is_not:
            return {field: {self.operator: self.rhs_obj}}
        else:
            return {field: {'$not': {self.operator: self.rhs_obj}}}


class HangingToken:

    def __init__(self, token):
        self.token: typing.Optional[
            typing.Union[Token, Op]
        ] = token


class Op:
    def __init__(self, lhs=None, rhs=None, left_tbl=None, params=None, op_name='generic'):
        self.lhs = lhs
        self.rhs = rhs
        self.params = params
        self.left_tbl = left_tbl
        self.is_not = False
        self._op_name = op_name
        self.precedence = OPERATOR_PRECEDENCE[op_name]

    @staticmethod
    def token_2_op(token, left_tbl, params):

        def resolve_token():
            logger.debug('resolving token: {}'.format(token.value))

            def token_unit_next(tkn, nxt_id):
                _, nxt_tok = tkn.token_next(nxt_id)


            def helper():
                nonlocal hanging_token, next_id, next_tok, hanging_token_used, kw

                if not hanging_token:
                    raise SQLDecodeError

                kw['lhs'] = hanging_token
                next_id, next_tok = token.token_next(next_id)
                hanging_token = HangingToken(next_tok)
                kw['rhs'] = hanging_token
                hanging_token_used = True

            nonlocal params
            next_id, next_tok = token.token_next(0)
            hanging_token = HangingToken(None)
            kw = {
                'params': params,
                'left_tbl': left_tbl
            }
            hanging_token_used = False

            while next_id:
                if next_tok.match(tokens.Keyword, 'AND'):
                    helper()
                    yield AndOp(**kw)

                elif next_tok.match(tokens.Keyword, 'OR'):
                    helper()
                    yield OrOp(**kw)

                elif next_tok.match(tokens.Keyword, 'IN'):
                    helper()
                    yield InOp(**kw)

                elif next_tok.match(tokens.Keyword, 'NOT'):
                    x, next_not = token.token_next(next_id)
                    if next_not.match(tokens.Keyword, 'IN'):
                        next_id, next_tok = token.token_next(next_id)
                        helper()
                        in_ob = InOp(**kw)
                        in_ob.is_not = True
                        yield in_ob
                    else:
                        helper()
                        yield NotOp(**kw)

                elif next_tok.match(tokens.Keyword, '.*', regex=True):
                    helper()
                    yield Op(**kw)

                elif next_tok.match(tokens.Punctuation, ')'):
                    break

                else:
                    hanging_token = HangingToken(next_tok)
                    hanging_token_used = False
                next_id, next_tok = token.token_next(next_id)

            if not hanging_token_used:
                if isinstance(hanging_token.token, Comparison):
                    yield AndOp(
                        lhs=HangingToken(None),
                        rhs=hanging_token,
                        params=params,
                        left_tbl=left_tbl)

                elif isinstance(hanging_token.token, Parenthesis):
                    yield Op.token_2_op(hanging_token.token, params=params, left_tbl=left_tbl)

                else:
                    raise SQLDecodeError

        def op_precedence(operator):
            nonlocal op_list
            if not op_list:
                op_list.append(operator)
                return

            for i in range(len(op_list)):
                if operator.precedence > op_list[i].precedence:
                    op_list.insert(i, operator)
                    break
            else:
                op_list.append(operator)

        op_list = []
        eval_op = None
        for op in resolve_token():
            op_precedence(op)

        while op_list:
            eval_op = op_list.pop(0)
            eval_op.evaluate()
        return eval_op

    def evaluate(self):
        self.lhs.token.rhs.token = self.rhs.token
        self.rhs.token.lhs.token = self.lhs.token

    def to_mongo(self):
        raise SQLDecodeError


class InOp(Op):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, op_name='IN')
        self.is_not = False
        self.field = None
        self._in = None

    def evaluate(self):
        if not (self.lhs and self.lhs.token):
            raise SQLDecodeError

        if not (self.rhs and self.rhs.token):
            raise SQLDecodeError

        if isinstance(self.lhs.token, Identifier):
            sql_ob = next(SQLToken.token_2_obj(self.lhs.token, params=self.params, left_tbl=self.left_tbl))
        else:
            raise SQLDecodeError

        if sql_ob.coll:
            if sql_ob.coll == self.left_tbl:
                self.field = sql_ob.field
            else:
                self.field = '{}.{}'.format(sql_ob.coll, sql_ob.field)
        else:
            self.field = sql_ob.field

        if not isinstance(self.rhs.token, Parenthesis):
            raise SQLDecodeError

        self._in = [ob for ob in SQLToken.token_2_obj(self.rhs.token, params=self.params, left_tbl=self.left_tbl)]

        self.lhs.token = self
        self.rhs.token = self

    def to_mongo(self):
        if self.is_not is False:
            op = '$in'
        else:
            op = '$nin'
        return {self.field: {op: self._in}}


class NotOp(Op):
    def __init__(self, *args, **kwargs):
        super(NotOp, self).__init__(*args, **kwargs, op_name='NOT')
        self.op = None

    def evaluate(self):
        if not (self.rhs and self.rhs.token):
            raise SQLDecodeError

        if isinstance(self.rhs.token, Parenthesis):
            self.op = self.token_2_op(self.rhs.token, params=self.params, left_tbl=self.left_tbl)
        elif isinstance(self.rhs.token, Comparison):
            self.op = SQLToken.token_2_obj(self.rhs.token, params=self.params, left_tbl=self.left_tbl)
        else:
            raise SQLDecodeError

        self.op.is_not = True

    def to_mongo(self):
        return self.op.to_mongo()


class AndOp(Op):
    def __init__(self, *args, **kwargs):
        super(AndOp, self).__init__(*args, **kwargs, op_name='AND')
        self._and = []

    def evaluate(self):
        # assert self.lhs or self.lhs.token
        if not (self.rhs and self.rhs.token):
            raise SQLDecodeError

        if self.lhs and self.lhs.token:
            if isinstance(self.lhs.token, AndOp):
                self._and.extend(self.lhs.token._and)

            elif isinstance(self.lhs.token, Op):
                self._and.append(self.lhs.token)

            elif isinstance(self.lhs.token, Parenthesis):
                self._and.append(self.token_2_op(self.lhs.token, params=self.params, left_tbl=self.left_tbl))

            elif isinstance(self.lhs.token, Comparison):
                self._and.append(next(SQLToken.token_2_obj(self.lhs.token, params=self.params, left_tbl=self.left_tbl)))

            else:
                raise SQLDecodeError

        if isinstance(self.rhs.token, AndOp):
            self._and.extend(self.rhs.token._and)

        elif isinstance(self.rhs.token, Op):
            self._and.append(self.rhs.token)

        elif isinstance(self.rhs.token, Parenthesis):
            self._and.append(self.token_2_op(self.rhs.token, params=self.params, left_tbl=self.left_tbl))

        elif isinstance(self.rhs.token, Comparison):
            self._and.append(next(SQLToken.token_2_obj(self.rhs.token, params=self.params, left_tbl=self.left_tbl)))

        elif isinstance(self.rhs.token, Identifier):
            self._and.append(self.token_2_op(self.rhs.token, params=self.params, left_tbl=self.left_tbl))
        else:
            raise SQLDecodeError

        self.lhs.token = self
        self.rhs.token = self

    def to_mongo(self):
        if self.is_not is False:
            ret_doc = {'$and': []}
            for itm in self._and:
                ret_doc['$and'].append(itm.to_mongo())
        else:
            ret_doc = {'$or': []}
            for itm in self._and:
                itm.is_not = True
                ret_doc['$or'].append(itm.to_mongo())

        return ret_doc


class OrOp(Op):
    def __init__(self, *args, **kwargs):
        super(OrOp, self).__init__(*args, **kwargs, op_name='OR')
        self._or = []

    def evaluate(self):
        if not (self.lhs and self.lhs.token):
            raise SQLDecodeError

        if not (self.rhs and self.rhs.token):
            raise SQLDecodeError

        if isinstance(self.lhs.token, OrOp):
            self._or.extend(self.lhs.token._or)
        elif isinstance(self.lhs.token, Op):
            self._or.append(self.lhs.token)
        elif isinstance(self.lhs.token, Parenthesis):
            self._or.append(self.token_2_op(self.lhs.token, params=self.params, left_tbl=self.left_tbl))
        elif isinstance(self.lhs.token, Comparison):
            self._or.append(next(SQLToken.token_2_obj(self.lhs.token, params=self.params, left_tbl=self.left_tbl)))
        else:
            raise SQLDecodeError

        if isinstance(self.rhs.token, OrOp):
            self._or.extend(self.rhs.token._or)
        elif isinstance(self.rhs.token, Op):
            self._or.append(self.rhs.token)
        elif isinstance(self.rhs.token, Parenthesis):
            self._or.append(self.token_2_op(self.rhs.token, params=self.params, left_tbl=self.left_tbl))
        elif isinstance(self.rhs.token, Comparison):
            self._or.append(next(SQLToken.token_2_obj(self.rhs.token, params=self.params, left_tbl=self.left_tbl)))
        else:
            raise SQLDecodeError

        self.lhs.token = self
        self.rhs.token = self

    def to_mongo(self):
        if not self.is_not:
            oper = '$or'
        else:
            oper = '$nor'

        ret_doc = {oper: []}
        for itm in self._or:
            ret_doc[oper].append(itm.to_mongo())
        return ret_doc


