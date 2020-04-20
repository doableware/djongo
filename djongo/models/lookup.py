from django.db.models import Transform, Lookup

class FieldNameTransform(Transform):

    def __init__(self, field_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_name = field_name

    def as_sql(self, compiler, connection, *args):
        qn = compiler.quote_name_unless_alias
        lhs = self.lhs
        path = self.field_name
        while isinstance(lhs, FieldNameTransform):
            path = f'{lhs.field_name}.{path}'
            lhs = lhs.lhs
        path = f'{lhs.target.column}.{path}'
        sql = f'{qn(lhs.alias)}.{qn(path)}'
        return sql, []


class FieldNameTransformFactory:

    def __init__(self, field_name):
        self.field_name = field_name

    def __call__(self, *args, **kwargs):
        return FieldNameTransform(self.field_name, *args, **kwargs)