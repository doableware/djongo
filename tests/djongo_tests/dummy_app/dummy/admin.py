from django.contrib import admin
# from .models import BlogPost, MultipleBlogPosts, Dummy2
from .basic_embedded_models import EEntry
from .basic_models import Entry, Author, Blog
# from .basic_embedded_models import Author, Entry
from .basic_array_models import ArrayEntry
from .basic_reference_models import ReferenceEntry, ReferenceAuthor

# Register your models here.
# admin.site.register(BlogPost)
# admin.site.register(Dummy2)
# admin.site.register(MultipleBlogPosts)

admin.site.register(Author)
admin.site.register(Blog)
admin.site.register(Entry)

admin.site.register(ArrayEntry)
admin.site.register(EEntry)
admin.site.register(ReferenceEntry)
admin.site.register(ReferenceAuthor)
