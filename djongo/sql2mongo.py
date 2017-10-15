from itertools import chain

from pymongo.cursor import Cursor as PymongoCursor
from pymongo.database import Database
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
    pass


class CollField(typing.NamedTuple):
    coll: str
    field: str


class SortOrder(typing.NamedTuple):
    coll_field: CollField
    ord: int


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

    def __init__(self,
                 connection: Database,
                 sql: str,
                 params: typing.Optional[list]):
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
        if sm_type in ('ALTER', 'DROP'):
            logger.debug('Not supported {}'.format(statement))
            return None

        try:
            return self.FUNC_MAP[sm_type](self, statement)
        except KeyError:
            logger.debug('\n Not implemented {} {}'.format(sm_type, statement))
            raise NotImplementedError('{} command not implemented for SQL {}'.format(sm_type, self._sql))

    def _create(self, sm):
        next_id, next_tok = sm.token_next(0)
        if next_tok.match(tokens.Keyword, 'TABLE'):
            next_id, next_tok = sm.token_next(next_id)
            table = next(SQLToken.iter_tokens(next_tok)).field
            self.db.create_collection(table)
            logger.debug('Created table {}'.format(table))

            next_id, next_tok = sm.token_next(next_id)
            if isinstance(next_tok, Parenthesis):
                for col in next_tok.value.strip('()').split(','):
                    if col.find('AUTOINCREMENT') != -1:
                        field = col[col.find('"')+1: col.rfind('"')]
                        self.db['__schema__'].insert_one({
                            'name': table,
                            'auto': {
                                'field_name': field,
                                'seq': 0
                            }
                        })
        else:
            logger.debug('Not supported {}'.format(sm))

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
            for sql in SQLToken.iter_tokens(next_tok):
                self.proj.coll_fields.append(CollField(sql.coll, sql.field))

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
                    join = InnerJoin()
                else:
                    join = OuterJoin()

                next_id, next_tok = sm.token_next(next_id)
                sql = next(SQLToken.iter_tokens(next_tok))
                right_tb = join.right_table = sql.field

                next_id, next_tok = sm.token_next(next_id)
                if not next_tok.match(tokens.Keyword, 'ON'):
                    raise SQLDecodeError('statement: {}'.format(sm))

                next_id, next_tok = sm.token_next(next_id)
                join_token = next(SQLToken.iter_tokens(next_tok))
                if right_tb == join_token.other_coll:
                    join.local_field = join_token.field
                    join.foreign_field = join_token.other_field
                    join.left_table = join_token.coll
                else:
                    join.local_field = join_token.other_field
                    join.foreign_field = join_token.field
                    join.left_table = join_token.other_coll

                self.joins.append(join)

            elif next_tok.match(tokens.Keyword, 'ORDER'):
                next_id, next_tok = sm.token_next(next_id)
                if not next_tok.match(tokens.Keyword, 'BY'):
                    raise SQLDecodeError('statement: {}'.format(sm))

                next_id, next_tok = sm.token_next(next_id)
                for order, sql in SQLToken.iter_tokens(next_tok):
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
        'DELETE': _delete,
        'CREATE': _create
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
                query_args['sort'] = [(s.coll_field.field, s.ord) for s in p_sql.sort]

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
        op = '$nin'
        return {self._field: {op: self._in}}


class InOp(_InNotInOp):

    def __init__(self, *args, **kwargs):
        super().__init__(name='IN', *args, **kwargs)
        self._fill_in(self.token.token_next(self._token_id)[1])

    def to_mongo(self):
        op = '$in'
        return {self._field: {op: self._in}}


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