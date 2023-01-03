import re
import typing
from collections import defaultdict
from itertools import chain

from sqlparse import tokens
from sqlparse.sql import Token, Parenthesis, Comparison, IdentifierList, Identifier, Function

from djongo.utils import encode_key
from . import query
from .functions import SQLFunc
from .sql_tokens import SQLToken, SQLStatement, SQLComparison, SQLIdentifier
from ..exceptions import SQLDecodeError


def re_index(value: str):
    match = re.match(r'%\(([0-9]+)\)s', value, flags=re.IGNORECASE)
    if match:
        index = int(match.group(1))
    else:
        match = re.match(r'NULL', value, flags=re.IGNORECASE)
        if not match:
            raise SQLDecodeError('Unable to find placeholder or NULL')
        index = None
    return index


def set_constant(op, token, attr='_constant', unwrap_dict=True):
    if not isinstance(token, Token):
        raise SQLDecodeError(f'{token} is not a Token!')
    index = re_index(token.value)
    setattr(op, attr, op.params[index] if index is not None else None)
    const_val = getattr(op, attr, None)
    if unwrap_dict and isinstance(const_val, dict):  # unwrap dict
        key, value = next(iter(const_val.items()))
        setattr(op, '_field_ext', key)
        setattr(op, attr, value)
    else:
        setattr(op, '_field_ext', None)


def parse_field(val, is_array_len=False, with_dollar=True):
    val = f'${val}' if with_dollar and isinstance(val, str) else val
    return {'$size': {"$ifNull": [val, []]}} if is_array_len else val


class _Op:

    def __init__(
            self,
            statement: SQLStatement,
            query: 'query.SelectQuery',
            params: tuple = None,
            name='generic'):
        super().__init__()
        self.lhs: typing.Optional[_Op] = None
        self.rhs: typing.Optional[_Op] = None

        if params is not None:
            self.params = params
        else:
            self.params = query.params
        self.query = query
        self.left_table = query.left_table

        self.statement = statement
        self.is_negated = False
        self._name = name
        self.precedence = OPERATOR_PRECEDENCE[name]

    def negate(self):
        raise NotImplementedError

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


class _BinaryOp(_Op):

    def __init__(self, *args, token='prev_token', **kwargs):
        super().__init__(*args, **kwargs)
        tok = SQLToken.token2sql(getattr(self.statement, token), self.query)
        if isinstance(tok, (SQLIdentifier, SQLFunc)):
            self._field = tok.field
        elif isinstance(tok, SQLComparison):
            self._field = SQLIdentifier(tok._token.left, tok.query).field
        else:
            raise SQLDecodeError(f'Unexpected token: {tok}')

    def negate(self):
        raise SQLDecodeError('Negating IN/NOT IN not supported')

    def to_mongo(self):
        raise NotImplementedError

    def evaluate(self):
        pass


class _InNotInOp(_BinaryOp):
    @property
    def is_in(self):
        return (isinstance(self, InOp) and not self.is_negated) or (isinstance(self, NotInOp) and self.is_negated)

    def _fill_in(self, token):
        self._in = []

        # Check for nested
        if token[1].ttype == tokens.DML:
            from .converters import NestedInQueryConverter

            self.query.nested_query = NestedInQueryConverter(token, self.query, 0)
            return

        for index in SQLToken.token2sql(token, self.query):
            if index is not None:
                self._in.append(self.params[index])
            else:
                self._in.append(None)

    def negate(self):
        self.is_negated = True

    def to_mongo(self):
        if self.query.nested_query is not None and not self._in:
            expr = {'$in': [f'${self._field}', '$_nested_in']}
            expr = {'$not': expr} if not self.is_in else expr
            return {'$expr': expr}
        else:
            expr = {'$in': self._in}
            expr = {'$not': expr} if not self.is_in else expr
            return {self._field: expr}


class NotInOp(_InNotInOp):
    def __init__(self, *args, token='prev_token', **kwargs):
        super().__init__(name='NOT IN', *args, token=token, **kwargs)
        self._fill_in(getattr(self.statement, token)[-1])


class InOp(_InNotInOp):
    def __init__(self, *args, token='prev_token', **kwargs):
        super().__init__(name='IN', *args, token=token, **kwargs)
        self._fill_in(getattr(self.statement, token)[-1])


class LikeOp(_BinaryOp):

    def __init__(self, *args, token='current_token', **kwargs):
        super().__init__(name='LIKE', *args, token=token, **kwargs)
        self._regex = None
        self._make_regex(getattr(self.statement, token))

    def _make_regex(self, token):
        index = SQLToken.placeholder_index(token.right)

        to_match = self.params[index]
        if isinstance(to_match, dict):
            field_ext, to_match = next(iter(to_match.items()))
            self._field += '.' + field_ext
        if not isinstance(to_match, str):
            raise SQLDecodeError
        # Ensure all regex special characters are handled
        to_match = re.escape(to_match)
        # Like expression special character - the expression above will escape \\
        to_match = to_match.replace('\\\\_', '_')
        # Like expression special character + ensure normal % is handled properly
        to_match = '%'.join(s.replace('%', '.*') for s in to_match.split('\\\\%'))
        self._regex = to_match

    def to_mongo(self):
        return {self._field: {'$regex': self._regex}}


class iLikeOp(LikeOp):
    def to_mongo(self):
        return {self._field: {
            '$regex': self._regex,
            '$options': 'im'
        }}


class RegexpOp(_BinaryOp):

    def __init__(self, *args, token='current_token', **kwargs):
        super().__init__(name='REGEXP', *args, token=token, **kwargs)
        self._regex = None
        self._make_regex(self.statement.next())

    def _make_regex(self, token):
        index = SQLToken.placeholder_index(token)

        to_match = self.params[index]
        if isinstance(to_match, dict):
            field_ext, to_match = next(iter(to_match.items()))
            self._field += '.' + field_ext
        if not isinstance(to_match, str):
            raise SQLDecodeError
        self._regex = to_match

    def to_mongo(self):
        return {self._field: {'$regex': self._regex}}


class IsOp(_BinaryOp):

    def __init__(self, *args, **kwargs):
        super().__init__(name='IS', *args, **kwargs)
        token = self.statement
        key = token.next()
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


class BetweenOp(_BinaryOp):

    def __init__(self, *args, **kwargs):
        super().__init__(name='BETWEEN', *args, **kwargs)
        token = self.statement

        lower = token.next()
        lower = SQLToken.placeholder_index(lower)
        self._lower = self.params[lower]

        _and = token.next()
        if not _and.match(tokens.Keyword, 'AND'):
            raise SQLDecodeError

        upper = token.next()
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


class _StatementParser:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ops: typing.List[_Op] = []
        self._cmp_ops: typing.List[_Op] = []
        self._op = None

    def _token2op(self,
                  tok: Token,
                  statement: SQLStatement) -> '_Op':
        op = None
        kw = {'statement': statement, 'query': self.query}
        if tok.match(tokens.Name.Placeholder, '%(.+)s', regex=True):
            return op

        if tok.match(tokens.Keyword, 'AND'):
            op = AndOp(**kw)

        elif tok.match(tokens.Keyword, 'OR'):
            op = OrOp(**kw)

        elif any(t.match(tokens.Comparison, 'NOT IN') for t in [tok, *getattr(tok, 'tokens', [])]):
            op = NotInOp(**kw, token='current_token')

        elif any(t.match(tokens.Comparison, 'IN') for t in [tok, *getattr(tok, 'tokens', [])]):
            op = InOp(**kw, token='current_token')

        elif tok.match(tokens.Keyword, 'NOT'):
            if statement.next_token.match(tokens.Keyword, 'IN'):
                op = NotInOp(**kw)
                statement.skip(1)
            else:
                op = NotOp(**kw)
        elif tok.value.endswith("REGEXP"):
            op = RegexpOp(**kw)

        elif isinstance(tok, Comparison) and 'iLIKE' in tok.normalized:
            op = iLikeOp(**kw)

        elif isinstance(tok, Comparison) and 'LIKE' in tok.normalized:
            op = LikeOp(**kw)

        elif tok.match(tokens.Keyword, 'BETWEEN'):
            op = BetweenOp(**kw)
            statement.skip(3)

        elif tok.match(tokens.Keyword, 'IS'):
            op = IsOp(**kw)

        elif isinstance(tok, Function) and statement.next_token.match(tokens.Keyword, 'IS'):
            statement.skip(2)
            op = IsOp(**kw)

        elif tok.value in JSON_OPERATORS:
            op = JSONOp(**kw)

        elif isinstance(tok, Comparison):
            op = CmpOp(tok, self.query)

        elif isinstance(tok, Parenthesis):
            if (tok[1].match(tokens.Name.Placeholder, '.*', regex=True)
                    or tok[1].match(tokens.Keyword, 'Null')
                    or isinstance(tok[1], IdentifierList)
                    or tok[1].ttype == tokens.DML
            ):
                pass
            else:
                op = ParenthesisOp(SQLStatement(tok), self.query)

        elif tok.match(tokens.Punctuation, (')', '(')):
            pass

        elif isinstance(tok, Identifier):
            t = statement.next_token
            if not t or t.match(tokens.Punctuation, (')', '(')) or t.match(tokens.Keyword, ('AND', 'OR')):
                op = ColOp(tok, self.query)
        else:
            raise SQLDecodeError

        return op

    def _statement2ops(self):
        def link_op():
            if prev_op is not None:
                prev_op.rhs = op
                op.lhs = prev_op

        statement = self.statement

        prev_op = None
        op = None
        for tok in statement:
            op = self._token2op(tok, statement)
            if not op:
                continue
            link_op()
            if isinstance(op, CmpOp):
                self._cmp_ops.append(op)
            if not isinstance(op, (CmpOp, ParenthesisOp, ColOp)):
                self._op_precedence(op)
            prev_op = op

        if prev_op.lhs is None:
            if isinstance(prev_op, (CmpOp, ParenthesisOp, ColOp)):
                self._ops.append(prev_op)

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
        for op in self._ops:
            op.evaluate()
        self._ops.clear()
        self._op = op


class WhereOp(_Op, _StatementParser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.statement.skip(2)
        self._statement2ops()
        self.evaluate()

    def negate(self):
        raise NotImplementedError

    def to_mongo(self):
        return self._op.to_mongo()


class ParenthesisOp(_Op, _StatementParser):

    def to_mongo(self):
        return self._op.to_mongo()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._statement2ops()

    def negate(self):
        for op in chain(self._ops, self._cmp_ops):
            op.negate()


class CmpOp(_Op):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._identifier = SQLToken.token2sql(self.statement.left, self.query)
        self._operator = OPERATOR_MAP[self.statement.token_next(0)[1].value]

        if isinstance(self.statement.right, Identifier):
            # Comparing against field in same doc vs a constant.
            self._is_right_constant = False
            self._right_identifier = SQLToken.token2sql(self.statement.right, self.query)
            if self._right_identifier.table != self._identifier.table:
                raise SQLDecodeError('Join using WHERE not supported')
        else:
            # Comparing with a constant
            self._is_right_constant = True
            set_constant(self, self.statement.right)

    def negate(self):
        self.is_negated = True

    def evaluate(self):
        pass

    def _compare_fields_to_mongo(self):
        """Comparison for fields in same document.
        https://docs.mongodb.com/manual/reference/operator/query/expr/#behavior
        """
        l_field = self.query.token_alias.similartoken2alias(self._identifier)
        l_field = f'${l_field}' if l_field else parse_field(self._identifier.field, self._identifier.is_array_len)
        r_field = self.query.token_alias.similartoken2alias(self._right_identifier)
        r_field = f'${r_field}' if r_field else parse_field(
            self._right_identifier.field, self._right_identifier.is_array_len)
        if not self.is_negated:
            return {'$expr': {self._operator: [l_field, r_field]}}
        else:
            return {'$expr': {'$not': {self._operator: [l_field, r_field]}}}

    def _compare_constant_to_mongo(self):
        field = self.query.token_alias.similartoken2alias(self._identifier)
        field = f'${field}' if field else parse_field(self._identifier.field, self._identifier.is_array_len)
        constant = parse_field(self._constant, False, with_dollar=False)
        if self._field_ext:
            field += '.' + self._field_ext
        if not self.is_negated:
            return {'$expr': {self._operator: [field, constant]}}
        else:
            return {'$expr': {'$not': {self._operator: [field, constant]}}}

    def to_mongo(self):
        if self._is_right_constant:
            return self._compare_constant_to_mongo()
        else:
            return self._compare_fields_to_mongo()


## Column operator - Fix for boolean fields, e.g. WHERE study.deleted
class ColOp(_Op):

    def __init__(self, *args, **kwargs):
        super().__init__(name='COL', *args, **kwargs)
        self._identifier = SQLToken.token2sql(self.statement, self.query)

    def negate(self):
        self.is_negated = True

    def to_mongo(self):
        return {self._identifier.field: not self.is_negated}

    def evaluate(self):
        pass


class JSONOp(_Op):

    def __init__(self, *args, **kwargs):
        super().__init__(name='JSON', *args, **kwargs)
        self._identifier = SQLIdentifier(self.statement.prev_token, self.query)
        self._operator = self.statement.current_token.value
        next_tok = self.statement.next_token

        if isinstance(next_tok, Identifier):
            # Comparing against field in same doc vs a constant.
            self._is_right_constant = False
            self._right = SQLToken.token2sql(next_tok, self.query)
            if self._right.table != self._identifier.table:
                raise SQLDecodeError('Join using WHERE not supported')
        else:
            # Comparing with a constant
            self._is_right_constant = True
            set_constant(self, next_tok, unwrap_dict=False, attr='_right')

    def negate(self):
        self.is_negated = True

    @staticmethod
    def lookup_to_mongo(value):
        # For $contains queries with lookups
        if not isinstance(value, dict):
            raise SQLDecodeError(f"Invalid $contains element: {value}")
        final = defaultdict(dict)
        for k, v in value.items():
            field = k.rsplit('__', 1)

            if len(field) == 1:  # simple equality
                final[field[0]] = v
                continue

            field, lookup = '.'.join(field[:-1]), field[-1]
            '''
            Supports mongo comparison operators: https://docs.mongodb.com/manual/reference/operator/query/
            By this design, we expect the user to mix traditional ORM query with mongo operators for $contains.
            Alternatively, we could also support django-based lookups
            (https://docs.djangoproject.com/en/3.2/ref/models/querysets/#field-lookups)
            but that would require more complicated transformations here.
            '''
            if lookup in ['in', 'nin', 'lt', 'lte', 'gt', 'gte', 'eq', 'ne']:
                final[field][f'${lookup}'] = v
            else:
                raise SQLDecodeError(f'Lookup {lookup} not supported in $contains')
        return dict(final)

    def evaluate(self):
        pass

    def to_mongo(self):
        operator = self._operator
        if self._is_right_constant:
            right = parse_field(self._right, False, with_dollar=False)
        else:
            right = parse_field(self._right.field, self._right.is_array_len, with_dollar=True)
        is_negated = self.is_negated

        field = parse_field(self._identifier.field, self._identifier.is_array_len, with_dollar=False)
        field_with_dollar = parse_field(self._identifier.field, self._identifier.is_array_len, with_dollar=True)
        field_parts = self._identifier.field.rsplit('.', 1)
        if self._identifier.is_array_len and operator not in ['$exact']:
            raise SQLDecodeError(
                f"Attempting to use array length ({self._identifier}) with {operator} which doesn't make sense.")

        if operator == '$exact':
            op = '$eq' if not is_negated else '$ne'
            op2 = '$in' if not is_negated else '$nin'
            if len(field_parts) > 1 and not self._identifier.is_array_len:
                parent_field = f'${field_parts[0]}'
                return {'$expr': {
                    '$cond': [
                        {'$eq': [{'$type': parent_field}, "array"]},
                        {op2: [right, field_with_dollar]},
                        {op: [field_with_dollar, right]}
                    ]}
                }
            else:
                return {'$expr': {op: [field_with_dollar, right]}}
        elif operator == '$contains':
            if isinstance(right, dict):
                # https://docs.mongodb.com/manual/tutorial/query-array-of-documents/#a-single-nested-document-meets-multiple-query-conditions-on-nested-fields
                if is_negated:
                    return {field: {'$not': {'$elemMatch': self.lookup_to_mongo(right)}}}
                else:
                    return {field: {'$elemMatch': self.lookup_to_mongo(right)}}
            elif isinstance(right, list):
                if is_negated:
                    return {field: {'$not': {'$all': right}}}
                else:
                    return {field: {'$all': right}}
            else:
                raise SQLDecodeError(f'Invalid params for $contains: {right}')
        elif operator == '$has_key':
            return {f'{field}.{encode_key(right)}': {'$exists': not is_negated}}
        elif operator == '$has_keys':
            return {f'{field}.{encode_key(const)}': {'$exists': not is_negated} for const in right}
        elif operator == '$has_any_keys':
            return {'$or': [{f'{field}.{encode_key(const)}': {'$exists': not is_negated}} for const in right]}
        else:
            raise SQLDecodeError(f'Invalid JSONOp: {operator}')


JSON_OPERATORS = ['$exact', '$contains', '$has_key', '$has_keys', '$has_any_keys']
OPERATOR_MAP = {
    '=': '$eq',
    '>': '$gt',
    '<': '$lt',
    '>=': '$gte',
    '<=': '$lte',
    '^': '$mod',
    '*': '$multiply',
    '/': '$divide',
    '%': '$mod',
    '+': '$add',
    '-': '$subtract',
}
OPERATOR_PRECEDENCE = {
    'MATH': 11,
    'COL': 10,
    'JSON': 9,
    'IS': 8,
    'BETWEEN': 7,
    'LIKE': 6,
    'iLIKE': 6,
    'REGEXP': 6,
    'IN': 5,
    'NOT IN': 4,
    'NOT': 3,
    'AND': 2,
    'OR': 1,
    'generic': 0
}
