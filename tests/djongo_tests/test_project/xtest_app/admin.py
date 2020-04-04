from django.contrib import admin

from xtest_app.models.array_field import ArrayFieldEntry as ArrayEntry
from xtest_app.models.basic_field import Entry, Author, Blog
from xtest_app.models.embedded_field import EmbeddedFieldEntry as EmbeddedEntry, EmbeddedDateEntry
from xtest_app.models.misc_field import ListEntry, DictEntry
from xtest_app.models.reference_field import ReferenceEntry, ReferenceAuthor
from xtest_app import models
# Register your models here.
# admin.site.register(BlogPost)
# admin.site.register(main_test2)
# admin.site.register(MultipleBlogPosts)

admin.site.register(Author)
admin.site.register(Blog)
admin.site.register(ArrayEntry)

admin.site.register(Entry)
admin.site.register(EmbeddedEntry)
admin.site.register(EmbeddedDateEntry)
admin.site.register(ReferenceEntry)
admin.site.register(ReferenceAuthor)
admin.site.register(ListEntry)
admin.site.register(DictEntry)

