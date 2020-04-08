from djongo import models
from .basic_field import NamedBlog, HeadlinedEntry


class EmbeddedFieldEntry(HeadlinedEntry):
    blog = models.EmbeddedField(
        model_container=NamedBlog
    )

    @classmethod
    def add_blog_field(cls,
                       model_container=NamedBlog,
                       **kwargs):
        pass

