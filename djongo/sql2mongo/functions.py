import typing

from sqlparse.sql import Token

from djongo.sql2mongo import SQLToken, SQLDecodeError, query


class SQLFunc:

    def __init__(self,
                 token: Token,
                 query: 'query.SelectQuery',
                 token_alias: 'query.TokenAlias' = None):
        self._token = token
        self._token_alias = token_alias
        self._query = query

        try:
            self._func_identifiers = SQLToken(token[0].get_parameters()[0], token_alias)
        except IndexError:
            if token[0].get_name() == 'COUNT':
                self._func_identifiers = None
            else:
                raise SQLDecodeError(f'Function {self._token} missing identifiers')



    def __repr__(self):
        return f'{type(self._token)}: {self._token}'

    def __hash__(self):
        return hash(self._token.value)

    @property
    def alias(self):
        return self._token.get_alias()

    @property
    def table(self):
        return self._func_identifiers and self._func_identifiers.table

    @property
    def column(self):
        return self._func_identifiers and self._func_identifiers.column

    @property
    def func(self):
        return self._token[0].get_name()

    @property
    def field(self):
        if self.table == self._query.left_table:
            field = self.column
        else:
            field = f'{self.table}.{self.column}'

        return field

    def to_mongo(self):
        field = f'${self.field}'
        if self.func == 'COUNT':
            if not self.column:
                return {'$sum': 1}

            else:
                return {
                    '$sum': {
                        '$cond': {
                            'if': {
                                '$gt': [field, None]
                            },
                            'then': 1,
                            'else': 0
                        }
                    }
                }
        elif self.func == 'MIN':
            return {'$min': field}
        elif self.func == 'MAX':
            return {'$max': field}
        elif self.func == 'SUM':
            return {'$sum': field}
        elif self.func == 'AVG':
            return {'$avg': field}
        else:
            raise SQLDecodeError