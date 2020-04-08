from django.contrib import admin

from xtest_app.models.array_field import ArrayFieldEntry as ArrayEntry
from xtest_app.models.basic_field import BasicRelatedEntry, BasicAuthor, BasicBlog
from xtest_app.models.embedded_field import EmbeddedFieldEntry as EmbeddedEntry, EmbeddedDateEntry
from xtest_app.models.misc_field import ListEntry, DictEntry
from xtest_app.models.reference_field import ReferenceEntry, ReferenceAuthor

admin.site.register(BasicAuthor)
admin.site.register(BasicBlog)
admin.site.register(ArrayEntry)

admin.site.register(BasicRelatedEntry)
admin.site.register(EmbeddedEntry)
admin.site.register(EmbeddedDateEntry)
admin.site.register(ReferenceEntry)
admin.site.register(ReferenceAuthor)
admin.site.register(ListEntry)
admin.site.register(DictEntry)

