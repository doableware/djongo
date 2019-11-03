import re
import typing
from itertools import chain

from sqlparse import tokens, parse as sqlparse
from sqlparse.sql import Token, Parenthesis, Comparison, IdentifierList, Identifier

from . import SQLDecodeError, SQLToken
from . import query


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


class _Op:

    def __init__(
            self,
            token_id: int,
            token: Token,
            query: 'query.SelectQuery',
            params: tuple = None,
            name='generic'):
        self.lhs: typing.Optional[_Op] = None
        self.rhs: typing.Optional[_Op] = None
        self._token_id = token_id

        if params is not None:
            self.params = params
        else:
            self.params = query.params
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


class _IdentifierOp(_Op):

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


class _InNotInOp(_IdentifierOp):

    def _fill_in(self, token):
        self._in = []

        # Check for nested
        if token[1].ttype == tokens.DML:
            from .converters import NestedInQueryConverter

            self.query.nested_query = NestedInQueryConverter(token, self.query, 0)
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


class LikeOp(_IdentifierOp):

    def __init__(self, *args, **kwargs):
        super().__init__(name='LIKE', *args, **kwargs)
        self._regex = None
        self._make_regex(self.token.token_next(self._token_id)[1])

    def _make_regex(self, token):
        index = SQLToken.placeholder_index(token)

        to_match = self.params[index]
        if isinstance(to_match, dict):
            field_ext, to_match = next(iter(to_match.items()))
            self._field += '.' + field_ext
        if not isinstance(to_match, str):
            raise SQLDecodeError

        to_match = to_match.replace('%', '.*')
        self._regex = '^' + to_match + '$'

    def to_mongo(self):
        return {self._field: {'$regex': self._regex}}


class iLikeOp(LikeOp):
    def to_mongo(self):
        return {self._field: {
            '$regex': self._regex,
            '$options': 'i'
        }}


class IsOp(_IdentifierOp):

    def __init__(self, *args, **kwargs):
        super().__init__(name='IS', *args, **kwargs)
        token = self.token
        tok_id, key = token.token_next(self._token_id)
        if key.match(tokens.Keyword, 'Null'):
            self._is_null = True
        elif key.match(tokens.Keyword, 'Not null'):
            self._is_null = False
        else:
            raise SQLDecodeError

    def negate(self):
        self.is_negated = True

    def to_mongo(self):
        is_null = not self._is_null if self.is_negated else self._is_null
        return {
            self._field: None if is_null else {'$ne': None}
        }


class BetweenOp(_IdentifierOp):

    def __init__(self, *args, **kwargs):
        super().__init__(name='BETWEEN', *args, **kwargs)
        token = self.token

        tok_id, lower = token.token_next(self._token_id)
        lower = SQLToken.placeholder_index(lower)
        self._lower = self.params[lower]

        tok_id, _and = token.token_next(tok_id)
        if not _and.match(tokens.Keyword, 'AND'):
            raise SQLDecodeError

        tok_id, upper = token.token_next(tok_id)
        upper = SQLToken.placeholder_index(upper)
        self._upper = self.params[upper]

    def negate(self):
        self.is_negated = True

    def to_mongo(self):
        if not self.is_negated:
            return {
                self._field: {
                    '$gte': self._lower,
                    '$lte': self._upper
                }
            }
        else:
            return {
                self._field: {
                    '$not': {
                        '$gte': self._lower,
                        '$lte': self._upper
                    }
                }
            }


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

            elif tok.match(tokens.Keyword, 'BETWEEN'):
                op = BetweenOp(**kw)
                link_op()
                self._op_precedence(op)
                for _ in range(3):
                    tok_id, _ = token.token_next(tok_id)

            elif tok.match(tokens.Keyword, 'IS'):
                op = IsOp(**kw)
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
        if isinstance(self._constant, dict):
            self._field_ext, self._constant = next(iter(self._constant.items()))
        else:
            self._field_ext = None

    def negate(self):
        self.is_negated = True

    def to_mongo(self):
        if self._identifier.table == self.left_table:
            field = self._identifier.column
        else:
            field = '{}.{}'.format(self._identifier.table, self._identifier.column)
        if self._field_ext:
            field += '.' + self._field_ext

        if not self.is_negated:
            return {field: {self._operator: self._constant}}
        else:
            return {field: {'$not': {self._operator: self._constant}}}


OPERATOR_MAP = {
    '=': '$eq',
    '>': '$gt',
    '<': '$lt',
    '>=': '$gte',
    '<=': '$lte',
}
OPERATOR_PRECEDENCE = {
    'IS': 8,
    'BETWEEN': 7,
    'LIKE': 6,
    'IN': 5,
    'NOT IN': 4,
    'NOT': 3,
    'AND': 2,
    'OR': 1,
    'generic': 0
}
