from django.contrib import admin
from .models import BlogPost, MultipleBlogPosts, Dummy2
# Register your models here.
admin.site.register(BlogPost)
admin.site.register(Dummy2)
admin.site.register(MultipleBlogPosts)
