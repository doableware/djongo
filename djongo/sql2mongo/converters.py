import abc
import ast
from collections import OrderedDict
from typing import Union as U, List, Optional as O

from sqlparse import tokens, parse as sqlparse
from sqlparse.sql import Parenthesis, IdentifierList, Comparison, Where

from . import query as query_module
from .functions import SQLFunc
from .operators import WhereOp
from .sql_tokens import SQLIdentifier, SQLConstIdentifier, SQLComparison, SQLToken, SQLStatement, SQLOperation
from ..exceptions import SQLDecodeError


class Converter:

    @abc.abstractmethod
    def __init__(
            self,
            query: U['query_module.SelectQuery',
            'query_module.BaseQuery'],
            statement: SQLStatement
    ):
        self.query = query
        self.statement = statement
        self.end_id = None
        self.parse()

    def parse(self):
        raise NotImplementedError

    def to_mongo(self):
        raise NotImplementedError


class ColumnSelectConverter(Converter):
    def __init__(self, query, statement):
        self.select_all = False
        self.num_columns = 0
        self.sql_tokens: List[U[SQLIdentifier, SQLFunc, SQLOperation]] = []
        super().__init__(query, statement)

    @property
    def sql_operations(self):
        return [t for t in self.sql_tokens if isinstance(t, SQLOperation)]

    def parse(self):
        tok = self.statement.next()

        if tok.match(tokens.Keyword, 'DISTINCT'):
            self.query.distinct = DistinctConverter(self.query, self.statement)

        else:
            for sql_token in SQLToken.tokens2sql(tok, self.query):
                self.sql_tokens.append(sql_token)

    def _to_mongo(self, toks):
        doc = {}

        def _to_mongo_value(s):
            if isinstance(s, SQLOperation):
                val = s.to_mongo()
            elif s.column and s.column.endswith('.len'):  # get size of array fields
                val = {'$size': {"$ifNull": [f"${s.column.rstrip('.len')}", []]}}
            else:
                val = f'${s.column}'
            return val

        for selected in toks:
            doc[selected.alias or selected.column] = _to_mongo_value(selected)
        return {'projection': doc}

    def to_mongo(self):
        return self._to_mongo(self.sql_tokens)


class AggColumnSelectConverter(ColumnSelectConverter):

    def _to_mongo(self, toks, ops_to_mongo=False):
        project = {}

        if any(isinstance(tok, SQLFunc) for tok in toks):
            # A SELECT func without groupby clause still needs a groupby in MongoDB
            return AggColumnSelectConverter._using_group_by(toks)
        elif isinstance(toks[0], SQLConstIdentifier):
            project[toks[0].alias] = toks[0].to_mongo()
        else:
            for selected in toks:
                if isinstance(selected, SQLOperation):
                    project[selected.alias] = selected.to_mongo() if ops_to_mongo else True
                else:
                    project[selected.field] = True

        return [{'$project': project}]

    def to_mongo_computed_fields(self):
        return self._to_mongo(self.sql_operations, ops_to_mongo=True)

    def to_mongo_normal_fields(self):
        return self._to_mongo(self.sql_tokens, ops_to_mongo=False)

    @classmethod
    def _using_group_by(cls, sql_tokens):
        group = {'_id': None}
        project = {'_id': False}
        has_agg_distinct = any(isinstance(selected, SQLFunc) and selected.is_distinct for selected in sql_tokens)

        ## FIX: agg(distinct) handler
        pipeline = cls._handle_agg_distinct(group, project, sql_tokens) if has_agg_distinct \
            else cls._handle_agg(group, project, sql_tokens)

        return pipeline

    @classmethod
    def _handle_agg_distinct(cls, group, project, sql_tokens):
        pipelines, keys = zip(*[cls._handle_agg_distinct_token(token, group, project) for token in sql_tokens])

        if len(pipelines) == 1:
            return pipelines[0] + [{'$project': project}]

        # use $facet when there are multiple selected columns
        facet, project = {}, {}
        for idx, pipeline in enumerate(pipelines):
            facet[str(idx)] = pipeline
            project[keys[idx]] = {'$arrayElemAt': [f"${idx}.{keys[idx]}", 0]}
        return [{'$facet': facet}, {'$project': project}]

    @classmethod
    def _handle_agg(cls, group, project, sql_tokens):
        for selected in sql_tokens:
            if isinstance(selected, SQLFunc):
                alias = cls._get_alias(selected)
                group[alias] = selected.to_mongo()
                project[alias] = True
            else:
                project[selected.field] = True
        return [{'$group': group}, {'$project': project}]

    @staticmethod
    def _get_alias(token):
        return token.alias or str(token.__hash__())

    @classmethod
    def _handle_agg_distinct_token(cls, token, group, project):
        if isinstance(token, SQLFunc) and token.is_distinct:
            # token = agg(distinct col)
            key = cls._get_alias(token)
            field = token.resolved_field
            group1 = {'_id': field, key: token.to_mongo()}
            group2 = {'_id': None, key: ast.literal_eval(str(token.to_mongo()).replace(field, f'${key}'))}
            pipeline = [{'$group': group1}, {'$group': group2}]
        elif isinstance(token, SQLFunc) and not token.is_distinct:
            # token = agg(col)
            key = cls._get_alias(token)
            group[key] = token.to_mongo()
            pipeline = [{'$group': group}]
        else:  # token = col
            key = token.field
            pipeline = [{'$group': group}]
        project[key] = True
        return pipeline, key


class FromConverter(Converter):

    def parse(self):
        tok = self.statement.next()
        sql = SQLToken.token2sql(tok, self.query)
        self.query.left_table = sql.table


class WhereConverter(Converter):
    nested_op: 'WhereOp' = None
    op: 'WhereOp' = None

    def parse(self):
        tok = self.statement.current_token
        self.op = WhereOp(
            statement=SQLStatement(tok),
            query=self.query,
            params=self.query.params
        )

    def to_mongo(self):
        return {'filter': self.op.to_mongo()}


class AggWhereConverter(WhereConverter):

    def to_mongo(self):
        return {'$match': self.op.to_mongo()}


class JoinConverter(Converter):

    @abc.abstractmethod
    def __init__(self, *args):
        self.left_table: O[str] = None
        self.right_table: O[str] = None
        self.left_column: O[str] = None
        self.right_column: O[str] = None
        super().__init__(*args)

    def parse(self):
        tok = self.statement.next()
        sql = SQLToken.token2sql(tok, self.query)
        right_table = self.right_table = sql.table

        tok = self.statement.next()
        if not tok.match(tokens.Keyword, 'ON'):
            raise SQLDecodeError

        tok = self.statement.next()
        if isinstance(tok, Parenthesis):
            tok = tok[1]

        sql = SQLToken.token2sql(tok, self.query)
        if right_table == sql.right_table:
            self.left_table = sql.left_table
            self.left_column = sql.left_column
            self.right_column = sql.right_column
        else:
            self.left_table = sql.right_table
            self.left_column = sql.right_column
            self.right_column = sql.left_column

    def _lookup(self):
        if self.left_table == self.query.left_table:
            local_field = self.left_column
        else:
            local_field = f'{self.left_table}.{self.left_column}'

        lookup = {
            '$lookup': {
                'from': self.right_table,
                'localField': local_field,
                'foreignField': self.right_column,
                'as': self.right_table
            }
        }

        return lookup


class InnerJoinConverter(JoinConverter):

    def __init__(self, *args):
        super().__init__(*args)

    def to_mongo(self):
        if self.left_table == self.query.left_table:
            match_field = self.left_column
        else:
            match_field = f'{self.left_table}.{self.left_column}'

        lookup = self._lookup()
        pipeline = [
            {
                '$match': {
                    match_field: {
                        '$ne': None,
                        '$exists': True
                    }
                }
            },
            lookup,
            {
                '$unwind': '$' + self.right_table
            }
        ]

        return pipeline


class OuterJoinConverter(JoinConverter):

    def __init__(self, *args):
        super().__init__(*args)

    def _null_fields(self, table):
        toks = self.query.selected_columns.sql_tokens
        fields = {}
        for tok in toks:
            if not (isinstance(tok, SQLFunc) and tok.is_wildcard) and tok.table == table:
                fields[tok.column] = None
        return fields

    def to_mongo(self):
        lookup = self._lookup()
        null_fields = self._null_fields(self.right_table)

        pipeline = [
            lookup,
            {
                '$unwind': {
                    'path': '$' + self.right_table,
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$addFields': {
                    self.right_table: {
                        '$ifNull': ['$' + self.right_table, null_fields]
                    }
                }
            }
        ]

        return pipeline


class LimitConverter(Converter):
    def __init__(self, *args):
        self.limit: O[int] = None
        super().__init__(*args)

    def parse(self):
        tok = self.statement.next()
        self.limit = int(tok.value)

    def to_mongo(self):
        return {'limit': self.limit}


class AggLimitConverter(LimitConverter):

    def to_mongo(self):
        return {'$limit': self.limit}


class OrderConverter(Converter):
    def __init__(self, *args):
        self.columns: List[SQLIdentifier] = []
        super().__init__(*args)

    def parse(self):
        tok = self.statement.next()
        self.columns.extend(SQLToken.tokens2sql(tok, self.query))

    def to_mongo(self):
        sort = [(tok.column, tok.order) for tok in self.columns]
        return {'sort': sort}


class SetConverter(Converter):

    def __init__(self, *args):
        self.sql_tokens: List[SQLComparison] = []
        super().__init__(*args)

    def parse(self):
        toks = self.parse_set_tokens()
        self.sql_tokens.extend(toks)

    def parse_set_tokens(self):
        # handle conditional sets
        ret = []
        tok = self.statement.next()
        while tok:
            prev_tok = self.statement.prev_token
            next_tok = self.statement.next_token
            if tok.value == '=':
                l = prev_tok[-1] if isinstance(prev_tok, IdentifierList) else prev_tok
                r = next_tok[0] if isinstance(next_tok, IdentifierList) else next_tok
                cmp = Comparison([l, tok, r])
                sql_cmp = SQLComparison(cmp, self.query)
                ret.append(sql_cmp)
            elif isinstance(tok, IdentifierList):
                start = 1 if prev_tok and prev_tok.value == '=' else 0
                end = -1 if next_tok and next_tok.value == '=' else None
                t = SQLToken.tokens2sql(IdentifierList(tokens=tok[start:end]), self.query)
                ret.extend(t)
            elif isinstance(tok, Comparison):
                ret.extend(SQLToken.tokens2sql(tok, self.query))
            if isinstance(next_tok, Where):
                break
            tok = self.statement.next()
        return ret

    def to_mongo(self):
        # use aggregation pipeline when updating using existing fields
        # https://www.mongodb.com/docs/manual/reference/method/db.collection.updateMany/#example-1--update-with-aggregation-pipeline-using-existing-fields
        uses_existing_fields = any(getattr(t, 'uses_existing_fields', False) for t in self.sql_tokens)
        _set = {'$set': {sql.left_column: sql.rhs for sql in self.sql_tokens}}
        _set = [_set] if uses_existing_fields else _set
        return {'update': _set}


class AggOrderConverter(OrderConverter):

    def to_mongo(self):
        sort = OrderedDict()
        for tok in self.columns:
            sort[tok.field] = tok.order

        return {'$sort': sort}


class _Tokens2Id:
    sql_tokens: List[
        U[SQLIdentifier, SQLFunc]
    ]
    query: U['query_module.SelectQuery',
    'query_module.BaseQuery']

    def to_id(self):
        _id = {}
        for iden in self.sql_tokens:
            ## FIX: FUNC('__col1')...FROM(SUBQUERY) syntax (fields weren't being renamed for outer query to refer)
            if iden.alias:
                _id[iden.alias] = f'${iden.field}'
            elif iden.column == iden.field:
                _id[iden.field] = f'${iden.field}'
            else:
                try:
                    _id[iden.table][iden.column] = f'${iden.field}'
                except KeyError:
                    _id[iden.table] = {iden.column: f'${iden.field}'}
            # if iden.table == self.query.left_table:
            #     _id[iden.column] = f'${iden.column}'
            # else:
            #     mongo_field = f'${iden.table}.{iden.column}'
            #     try:
            #         _id[iden.table][iden.column] = mongo_field
            #     except KeyError:
            #         _id[iden.table] = {iden.column: mongo_field}

        return _id


class DistinctConverter(ColumnSelectConverter, _Tokens2Id):
    def __init__(self, *args):
        super().__init__(*args)

    def to_mongo(self):
        _id = self.to_id()

        return [
            {
                '$group': {
                    '_id': _id
                }
            },
            {
                '$replaceRoot': {
                    'newRoot': '$_id'
                }
            }
        ]


class NestedInQueryConverter(Converter):

    def __init__(self, token, *args):
        self._token = token
        self._in_query: O['query_module.SelectQuery'] = None
        super().__init__(*args)

    def parse(self):
        from .query import SelectQuery

        self._in_query = SelectQuery(
            self.query.db,
            self.query.connection_properties,
            sqlparse(self._token.value[1:-1])[0],
            self.query.params
        )

    def to_mongo(self):
        return [
            {
                '$lookup': {
                    'from': self._in_query.left_table,
                    'pipeline': self._in_query._make_pipeline(),
                    'as': '_nested_in'
                }
            },
            *[
                {
                    '$addFields': {
                        '_nested_in': {
                            '$map': {
                                'input': '$_nested_in',
                                'as': 'lookup_result',
                                'in': '$$lookup_result.' + t.column
                            }
                        }
                    }
                } for t in self._in_query.selected_columns.sql_tokens
            ]
        ]


## FIX: FROM(SUBQUERY)
class NestedFromQueryConverter(Converter):

    def __init__(self, *args):
        self._from_query: O['query_module.SelectQuery'] = None
        super().__init__(*args)

    def parse(self):
        from .query import SelectQuery
        tok = self.statement.next()

        self._from_query = SelectQuery(
            self.query.db,
            self.query.connection_properties,
            sqlparse(tok[0].value[1:-1])[0],
            self.query.params
        )
        self.query.left_table = self._from_query.left_table

    def to_mongo(self):
        return self._from_query._make_pipeline()


class HavingConverter(Converter):
    nested_op: 'WhereOp' = None
    op: 'WhereOp' = None

    def __init__(self,
                 query: U['query_module.SelectQuery',
                 'query_module.BaseQuery'],
                 statement: SQLStatement):
        super().__init__(query, statement)

    def parse(self):
        cutoff = 2
        next_next_token_idx = self.statement._tok_id + 4
        if next_next_token_idx < len(self.statement._statement.tokens) and self.statement._statement[
            next_next_token_idx].match(tokens.Keyword, 'IS'):
            cutoff += 4
        tok = self.statement[:cutoff + 1]

        self.op = WhereOp(
            statement=tok,
            query=self.query,
            params=self.query.params
        )
        self.statement.skip(cutoff)

    def to_mongo(self):
        return {'$match': self.op.to_mongo()}


class GroupbyConverter(Converter, _Tokens2Id):

    def __init__(self, *args):
        self.sql_tokens: List[SQLToken] = []
        super().__init__(*args)

    def parse(self):
        tok = self.statement.next()
        if tok.match(tokens.Keyword, 'BY'):
            tok = self.statement.next()
        self.sql_tokens.extend(SQLToken.tokens2sql(tok, self.query))

    def to_mongo(self):
        _id = self.to_id()

        group = {
            '_id': _id
        }
        project = {
            '_id': False
        }
        for selected in self.query.selected_columns.sql_tokens:
            if isinstance(selected, SQLIdentifier):
                project[selected.field] = f'$_id.{selected.field}'
            else:
                ## FIX: issue occurs when there's no explicit alias and we're dealing with FROM(subquery)
                alias = selected.alias or str(selected.__hash__())
                project[alias] = True
                group[alias] = selected.to_mongo()

        pipeline = [
            {
                '$group': group
            },
            {
                '$project': project
            }
        ]

        return pipeline


class OffsetConverter(Converter):
    def __init__(self, *args):
        self.offset: int = None
        super().__init__(*args)

    def parse(self):
        tok = self.statement.next()
        self.offset = int(tok.value)

    def to_mongo(self):
        return {'skip': self.offset}


class AggOffsetConverter(OffsetConverter):

    def to_mongo(self):
        return {'$skip': self.offset}
