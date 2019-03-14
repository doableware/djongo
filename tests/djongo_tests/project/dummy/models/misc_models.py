from djongo import models


class ListEntry(models.Model):
    _id = models.ObjectIdField()
    headline = models.CharField(max_length=255)
    authors = models.ListField()

    def __str__(self):
        return self.headline

class DictEntry(models.Model):
    _id = models.ObjectIdField()
    headline = models.CharField(max_length=255)
    blog = models.DictField()

    def __str__(self):
        return self.headline

