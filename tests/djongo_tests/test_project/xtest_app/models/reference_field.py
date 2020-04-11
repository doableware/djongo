from djongo import models
from .basic_field import NamedAuthor, HeadlinedEntry


# class ReferenceAuthor(NamedAuthor):
#     email = models.EmailField()
#     _id = models.ObjectIdField()
#
#
# class ReferenceEntry(HeadlinedEntry):
#     authors = models.ArrayReferenceField(ReferenceAuthor)

