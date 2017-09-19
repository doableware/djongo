from django.db import models


# Create your models here.
class Dummy(models.Model):

    test = models.CharField(max_length=10)

