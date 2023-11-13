import abc

from sqlparse.sql import Token

from ..exceptions import SQLDecodeError
from .sql_tokens import AliasableToken, SQLToken
from . import query as query_module
from typing import Union as U


class SQLFunc(AliasableToken):

    @abc.abstractmethod
    def __init__(self, *args):
        super().__init__(*args)

    @staticmethod
    def token2sql(token: Token,
                  query: 'query_module.BaseQuery'
                  ) -> U['CountFunc', 'DateTrunc',
                         'SimpleFunc']:
        func = token[0].get_name()
        if func == 'COUNT':
            return CountFunc.token2sql(token, query)
        elif func == 'DATE_TRUNC':
            return DateTrunc(token, query)
        else:
            return SimpleFunc(token, query)

    @property
    def alias(self) -> str:
        return self._token.get_alias()

    @property
    def func(self) -> str:
        return self._token[0].get_name()

    @abc.abstractmethod
    def to_mongo(self) -> dict:
        raise NotImplementedError


class SingleParamFunc(SQLFunc):
    def __init__(self, *args):
        super().__init__(*args)
        if self.alias:
            param = self._token[0].get_parameters()[0]
        else:
            param = self._token.get_parameters()[0]
        self.iden = SQLToken.token2sql(param, self.query)

    @property
    def table(self):
        return self.iden.table

    @property
    def column(self):
        return self.iden.column

    @property
    def field(self):
        if self.alias:
            return self.alias
        try:
            alias = self.query.token_alias.token2alias[self]
        except KeyError:
            alias = self.column
        return alias

    @abc.abstractmethod
    def to_mongo(self) -> dict:
        raise NotImplementedError


class DateTrunc(SQLFunc):
    """Allows to truncate datetime fields to any of their parts"""
    lookup_type = 'day'

    def __init__(self, *args):
        super().__init__(*args)
        if self.alias:
            param = list(self._token[0].get_parameters())
            self.lookup_type = param[0].value.lower()
            param = param[1]
        else:
            param = list(self._token.get_parameters())
            self.lookup_type = param[0].value.lower()
            param = param[1]
        self.iden = SQLToken.token2sql(param, self.query)

    @property
    def table(self):
        return self.iden.table

    @property
    def column(self):
        return self.iden.column

    @property
    def field(self):
        if self.alias:
            return self.alias
        try:
            alias = self.query.token_alias.token2alias[self]
        except KeyError:
            alias = self.column
        return alias

    def to_mongo(self):
        field = f'${self.iden.field}'
        fields = ['year', 'month', 'day', 'hour', 'minute', 'second']
        format = ('%Y-', '%m', '-%d', 'T%H:', '%i', ':%sZ')
        format_def = ('0000-', '01', '-01', 'T00:', '00', ':00Z')
        # Pulled from existing mysql driver
        # TODO there's maybe a better way to send this but I had no time to do it
        try:
            i = fields.index(self.lookup_type) + 1
        except ValueError:
            return field
        else:
            format_str = ''.join(format[:i] + format_def[i:])
        return {f'$dateFromString': {'dateString': {'$dateToString': {'format': format_str, 'date': field}}}}


class CountFunc(SQLFunc):

    @staticmethod
    def token2sql(token: Token,
                  query: 'query_module.BaseQuery'
                  ) -> U['CountFuncAll',
                         'CountFuncSingle']:
        try:
            token[0].get_parameters()[0]
        except IndexError:
            return CountFuncAll(token, query)
        else:
            return CountFuncSingle(token, query)

    @abc.abstractmethod
    def to_mongo(self):
        raise NotImplementedError


class CountFuncAll(CountFunc):

    def __init__(self, *args):
        super().__init__(*args)

    def to_mongo(self):
        return {'$sum': 1}


class CountFuncSingle(CountFunc, SingleParamFunc):

    def to_mongo(self):
        field = f'${self.iden.field}'
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


class SimpleFunc(SingleParamFunc):

    def to_mongo(self):
        field = f'${self.iden.field}'
        if self.func in ('MIN', 'MAX', 'SUM', 'AVG'):
            return {f'${self.func.lower()}': field}
        else:
            raise SQLDecodeError(f'Unsupported func: {self.func}')


