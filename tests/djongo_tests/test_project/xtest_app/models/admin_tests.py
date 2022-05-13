from djongo import models
from .basic_field import NamedAuthor, HeadlinedEntry


class ArrayFieldEntry(HeadlinedEntry):
    authors = models.ArrayField(
        model_container=NamedAuthor
    )


