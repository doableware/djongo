from django.contrib import admin
from dummy.models.basic_embedded_models import EmbeddedEntry
from dummy.models.basic_models import Entry, Author, Blog
from dummy.models.basic_array_models import ArrayEntry
from dummy.models.basic_reference_models import ReferenceEntry, ReferenceAuthor

# Register your models here.
# admin.site.register(BlogPost)
# admin.site.register(Dummy2)
# admin.site.register(MultipleBlogPosts)

admin.site.register(Author)
admin.site.register(Blog)
admin.site.register(Entry)

admin.site.register(ArrayEntry)
admin.site.register(EmbeddedEntry)
admin.site.register(ReferenceEntry)
admin.site.register(ReferenceAuthor)
