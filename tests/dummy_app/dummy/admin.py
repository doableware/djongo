from django.contrib import admin
from .models import Dummy, Dummies, Dummy2
# Register your models here.
admin.site.register(Dummy)
admin.site.register(Dummy2)
admin.site.register(Dummies)
