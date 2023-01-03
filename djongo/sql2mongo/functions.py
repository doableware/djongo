from sqlparse import tokens, parse as sqlparse
from sqlparse.sql import Function, Case

from .sql_tokens import AliasableToken, SQLToken, SQLStatement
from ..exceptions import SQLDecodeError


class SQLFunc(AliasableToken):
    def __init__(self, *args):
        super().__init__(*args)

    @property
    def func_tok(self):
        if isinstance(self._token, Function):
            return self._token
        elif isinstance(self._token[0], Function):
            return self._token[0]
        else:
            raise SQLDecodeError('Not a function')

    @property
    def func(self) -> str:
        return self.func_tok.get_name()

    @property
    def parameters(self):
        return self.func_tok.get_parameters()

    @property
    def identifier(self):
        if not self.parameters[0]:
            return None
        return SQLToken.token2sql(self.parameters[0], self.query)

    @property
    def field(self):
        return self.alias if self.alias else self.query.token_alias.token2alias[self]

    @property
    def table(self):
        return self.identifier.table

    @property
    def column(self):
        return self.identifier.column

    @property
    def resolved_field(self):
        if self.conditional_cases:
            """Deal with condition aggregation functions - agg(case when .. then .. else ..)
            Might not be the best place to put this since it's also possible to have conditional cases w/o aggregation.
            But we can refactor it when the need comes.
            """
            from .operators import WhereOp
            cases = []
            for c in self.conditional_cases:
                case_toks, then_toks = c
                case_val, then_val = None, None
                if case_toks:
                    case_stmt = SQLStatement(sqlparse(' '.join(str(s) for s in case_toks))[0])
                    case_op = WhereOp(statement=case_stmt, query=self.query, params=self.query.params)
                    case_val = case_op.to_mongo()
                if then_toks:
                    then_stmt = SQLStatement(sqlparse(' '.join(str(s) for s in then_toks[1:]))[0])
                    then_val = SQLToken.token2sql(then_stmt.next(), query=self.query).to_mongo()
                cases.append((case_val, then_val))
            if not cases:
                raise SQLDecodeError
            cases_to_mongo = {'$cond': [cases[0][0], cases[0][1]]}
            cond = cases_to_mongo['$cond']
            for c in cases[1:]:
                if c[0]:  # a WHEN..THEN vs ELSE
                    nested_cond = {'$cond': [c[0], c[1]]}
                    cond.append(nested_cond)
                else:
                    cond.append(c[1])
                cond = nested_cond['$cond']
            return cases_to_mongo
        else:
            """FIX: FUNC('__col1')...FROM(SUBQUERY) syntax (field becomes '__col1.__col1')"""
            iden = self.identifier
            return f'${iden.column}' if iden.column == iden.table else f'${iden.field}'

    @property
    def is_distinct(self) -> str:
        """ to_mongo not handled yet """
        return self.func_tok[1][1].match(tokens.Keyword, 'DISTINCT')

    @property
    def conditional_cases(self):
        t = self.func_tok[1][1]
        if not isinstance(t, Case):
            return None
        return t.get_cases(skip_ws=True)

    @property
    def is_wildcard(self):
        return self.func_tok[1][1].ttype == tokens.Wildcard

    def to_mongo(self) -> dict:
        if self.func in ('MIN', 'MAX', 'SUM', 'AVG'):
            return {f'${self.func.lower()}': self.resolved_field}
        elif self.func == 'COUNT':
            if self.is_wildcard:
                return {'$sum': 1}
            return {
                '$sum': {
                    '$cond': {
                        'if': {
                            '$gt': [self.resolved_field, None]
                        },
                        'then': 1,
                        'else': 0
                    }
                }
            }
        else:
            raise SQLDecodeError(f'Unsupported func: {self.func}')
