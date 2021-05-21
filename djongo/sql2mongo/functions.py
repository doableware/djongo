import abc

from sqlparse.sql import Token, Identifier
from sqlparse import tokens

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
                  ) -> U['CountFunc',
                         'SimpleFunc']:
        ## FIX: agg(distinct)
        if isinstance(token[0], Identifier) and token[1][1].match(tokens.Keyword, 'DISTINCT'):
            token.is_agg_distinct = True
        else:
            token.is_agg_distinct = False

        func = token[0].get_name()
        if func == 'COUNT':
            return CountFunc.token2sql(token, query)
        else:
            return SimpleFunc(token, query)

    @property
    def is_agg_distinct(self) -> str:
        return self._token.is_agg_distinct

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
        alias = self.query.token_alias.token2alias[self]
        return alias

    @abc.abstractmethod
    def to_mongo(self) -> dict:
        raise NotImplementedError


class CountFunc(SQLFunc):

    @staticmethod
    def token2sql(token: Token,
                  query: 'query_module.BaseQuery'
                  ) -> U['CountFuncAll',
                         'CountFuncSingle']:
        try:
            ## FIX: COUNT(DISTINCT COL)
            ## TODO: This just gets the parser through the token, but distinct logic is not actually handled yet.
            if isinstance(token[0], Identifier):
                token.get_parameters()[0]
            else:
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
        ## FIX: FUNC('__col1')...FROM(SUBQUERY) syntax (field becomes '__col1.__col1')
        field = f'${self.iden.column}' if self.iden.column == self.iden.table else f'${self.iden.field}'

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
        ## FIX: FUNC('__col1')...FROM(SUBQUERY) syntax (field becomes '__col1.__col1')
        field = f'${self.iden.column}' if self.iden.column == self.iden.table else f'${self.iden.field}'

        if self.func in ('MIN', 'MAX', 'SUM',
                         'AVG'):
            return {f'${self.func.lower()}': field}
        else:
            raise SQLDecodeError(f'Unsupported func: {self.func}')


