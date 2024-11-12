from django.contrib import admin

from aut.models.admin_tests import ArrayFieldEntry as ArrayEntry
from aut.models.various_fields import BasicRelatedEntry, BasicAuthor, BasicBlog, EmbeddedFieldEntry as EmbeddedEntry

# from xtest_app.models.reference_field import ReferenceEntry, ReferenceAuthor

admin.site.register(BasicAuthor)
admin.site.register(BasicBlog)
admin.site.register(ArrayEntry)

admin.site.register(BasicRelatedEntry)
# admin.site.register(EmbeddedEntry)
# admin.site.register(EmbeddedDateEntry)
# admin.site.register(ReferenceEntry)
# admin.site.register(ReferenceAuthor)


