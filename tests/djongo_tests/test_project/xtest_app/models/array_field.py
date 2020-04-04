from djongo import models


class Author(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class ArrayFieldEntry(models.Model):
    headline = models.CharField(max_length=255)
    authors = models.ArrayField(
        model_container=Author
    )
    _id = models.ObjectIdField()

    def __str__(self):
        return self.headline

