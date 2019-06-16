from django.contrib import admin

from main_test.models.array_models import ArrayEntry
from main_test.models.basic_models import Entry, Author, Blog
from main_test.models.embedded_models import EmbeddedEntry, EmbeddedDateEntry
from main_test.models.misc_models import ListEntry, DictEntry
from main_test.models.reference_models import ReferenceEntry, ReferenceAuthor

# Register your models here.
# admin.site.register(BlogPost)
# admin.site.register(main_test2)
# admin.site.register(MultipleBlogPosts)

admin.site.register(Author)
admin.site.register(Blog)
admin.site.register(Entry)

admin.site.register(ArrayEntry)
admin.site.register(EmbeddedEntry)
admin.site.register(EmbeddedDateEntry)
admin.site.register(ReferenceEntry)
admin.site.register(ReferenceAuthor)
admin.site.register(ListEntry)
admin.site.register(DictEntry)

