from djongo import models
from .basic_field import NamedBlog, HeadlinedEntry


# Used purely for type checking
class EmbeddedFieldEntry(HeadlinedEntry):
    blog = models.EmbeddedField(
        model_container=NamedBlog
    )

    class Meta:
        abstract = True


# Used purely for type checking
class ArrayFieldEntry(HeadlinedEntry):
    blog = models.ArrayField(
        model_container=NamedBlog
    )

    class Meta:
        abstract = True

