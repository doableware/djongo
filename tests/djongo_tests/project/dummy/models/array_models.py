from djongo import models


class ArrayAuthor(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class ArrayEntry(models.Model):
    headline = models.CharField(max_length=255)
    authors = models.ArrayModelField(
        model_container=ArrayAuthor
    )

    def __str__(self):
        return self.headline

