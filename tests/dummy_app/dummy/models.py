from djongo import models

# Create your models here.

class Embedded(models.Model):
    text = models.CharField(max_length=100)

    class Meta:
        abstract = True


class Dummy(models.Model):

    test = models.CharField(max_length=10)
    embedded = models.EmbeddedModelField(model_container=Embedded)
