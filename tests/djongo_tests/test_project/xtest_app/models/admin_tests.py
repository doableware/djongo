from djongo import models
from .basic_field import NamedAuthor, HeadlinedEntry


class ArrayFieldEntry(HeadlinedEntry):
    _id = models.AutoField(primary_key=True)
    authors = models.ArrayField(
        model_container=NamedAuthor
    )


