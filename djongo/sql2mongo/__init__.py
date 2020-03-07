import re
import typing

from pymongo import ASCENDING, DESCENDING
from sqlparse import tokens, parse as sqlparse
from sqlparse.sql import Token, Identifier, Comparison, Parenthesis, IdentifierList, Statement

djongo_access_url = 'https://www.patreon.com/nesdis'
_printed_features = set()


class SQLDecodeError(ValueError):

    def __init__(self, err_sql=None):
        self.err_sql = err_sql


class NotSupportedError(ValueError):

    def __init__(self, keyword=None):
        self.keyword = keyword


class MigrationError(Exception):

    def __init__(self, field):
        self.field = field


def print_warn(feature=None, message=None):
    if feature not in _printed_features:
        message = ((message or f'This version of djongo does not support {feature} fully. ')
                   + f'Visit {djongo_access_url}')
        print(message)
        _printed_features.add(feature)


class SQLFunc:

    def __init__(self, token: Token, alias2token=None):
        self._token = token

        try:
            self._iden = SQLToken(token[0].get_parameters()[0], alias2token)
        except IndexError:
            if token[0].get_name() == 'COUNT':
                self._iden = None
            else:
                raise

        self.alias2token: typing.Dict[str, SQLToken] = alias2token

    @property
    def alias(self):
        return self._token.get_alias()

    @property
    def table(self):
        return self._iden.table if self._iden else None

    @property
    def column(self):
        return self._iden.column if self._iden else None

    @property
    def func(self):
        return self._token[0].get_name()

    def to_mongo(self, query):
        if self.table == query.left_table:
            field = self.column
        else:
            field = f'{self.table}.{self.column}'

        if self.func == 'COUNT':
            if not self.column:
                return {'$sum': 1}

            else:
                return {
                    '$sum': {
                        '$cond': {
                            'if': {
                                '$gt': ['$' + field, None]
                            },
                            'then': 1,
                            'else': 0
                        }
                    }
                }
        elif self.func == 'MIN':
            return {'$min': '$' + field}
        elif self.func == 'MAX':
            return {'$max': '$' + field}
        elif self.func == 'SUM':
            return {'$sum': '$' + field}
        elif self.func == 'AVG':
            return {'$avg': '$' + field}
        else:
            raise SQLDecodeError


class SQLToken:

    def __init__(self, token: Token, alias2token=None):
        self._token = token
        self.alias2token: typing.Dict[str, SQLToken] = alias2token

    def has_parent(self):
        return self._token.get_parent_name()

    @property
    def table(self):
        if not isinstance(self._token, Identifier):
            raise SQLDecodeError

        name = self._token.get_parent_name()
        if name is None:
            name = self._token.get_real_name()
        else:
            if name in self.alias2token:
                return self.alias2token[name].table
            return name

        if name is None:
            raise SQLDecodeError

        if self.alias2token and name in self.alias2token:
            return self.alias2token[name].table
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

        lhs = SQLToken(self._token.left, self.alias2token)
        return lhs.table

    @property
    def left_column(self):
        if not isinstance(self._token, Comparison):
            raise SQLDecodeError

        lhs = SQLToken(self._token.left, self.alias2token)
        return lhs.column

    @property
    def right_table(self):
        if not isinstance(self._token, Comparison):
            raise SQLDecodeError

        rhs = SQLToken(self._token.right, self.alias2token)
        return rhs.table

    @property
    def right_column(self):
        if not isinstance(self._token, Comparison):
            raise SQLDecodeError

        rhs = SQLToken(self._token.right, self.alias2token)
        return rhs.column

    @property
    def lhs_column(self):
        if not isinstance(self._token, Comparison):
            raise SQLDecodeError

        lhs = SQLToken(self._token.left, self.alias2token)
        return lhs.column

    @property
    def rhs_indexes(self):
        if not self._token.right.ttype == tokens.Name.Placeholder:
            if self._token.right.match(tokens.Keyword, 'NULL'):
                return None
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


ORDER_BY_MAP = {
    'ASC': ASCENDING,
    'DESC': DESCENDING
}


class SQLStatement:

    @property
    def current_token(self) -> Token:
        return self._statement[self._tok_id]

    def __init__(self, statement: typing.Union[Statement, Token]):
        self._statement = statement
        self._tok_id = 0

    def __getattr__(self, item):
        return getattr(self._statement, item)

    def __iter__(self) -> Token:
        token = self._statement[self._tok_id]
        while self._tok_id is not None:
            yield token
            self._tok_id, token = self._statement.token_next(self._tok_id)

    def __repr__(self):
        return str(self._statement)

    def __getitem__(self, item: slice):
        start = (item.start or 0) + self._tok_id
        stop = item.stop and self._tok_id + item.stop
        sql = ''.join(str(tok) for tok in self._statement[start:stop])
        sql = sqlparse(sql)[0]
        return SQLStatement(sql)

    def next(self) -> Token:
        self._tok_id, token = self._statement.token_next(self._tok_id)
        return token

    def skip(self, num):
        self._tok_id += num

    @property
    def prev_token(self) -> Token:
        return self._statement.token_prev(self._tok_id)[1]

    @property
    def next_token(self) -> Token:
        return self._statement.token_next(self._tok_id)[1]

# Fixes some circular import issues
from . import query
from . import converters