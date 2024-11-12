from djongo import models
from .various_fields import NamedAuthor, HeadlinedEntry


class ArrayFieldEntry(HeadlinedEntry):
    authors = models.ArrayField(
        model_container=NamedAuthor
    )


