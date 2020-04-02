from django.db.models.lookups import BuiltinLookup
from djongo.models import ListField


@ListField.register_lookup
class ContainsAny(BuiltinLookup):
    lookup_name = 'contains_any'
