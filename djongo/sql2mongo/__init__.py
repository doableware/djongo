import re
import typing

from pymongo import ASCENDING, DESCENDING
from sqlparse import tokens
from sqlparse.sql import Token, Identifier, Comparison, Parenthesis, IdentifierList


class SQLDecodeError(ValueError):

    def __init__(self, err_sql=None):
        self.err_sql = err_sql


class MigrationError(Exception):

    def __init__(self, field):
        self.field = field


class SQLFunc:

    def __init__(self, token: Token, alias2op=None):
        self._token = token

        try:
            self._iden = SQLToken(token[0].get_parameters()[0], alias2op)
        except IndexError:
            if token[0].get_name() == 'COUNT':
                self._iden = None
            else:
                raise

        self.alias2op: typing.Dict[str, SQLToken] = alias2op

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

    def __init__(self, token: Token, alias2op=None):
        self._token = token
        self.alias2op: typing.Dict[str, SQLToken] = alias2op

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

# Fixes some circular import issues
from . import query
from . import converters