from djongo import models


class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class EmbeddedFieldEntry(models.Model):
    blog = models.EmbeddedField(
        model_container=Blog
    )
    headline = models.CharField(max_length=255)
    _id = models.ObjectIdField()

    def __str__(self):
        return self.headline


class DateBlog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()
    modified_blog = models.DateField()

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class EmbeddedDateEntry(models.Model):
    blog = models.EmbeddedField(
        model_container=DateBlog
    )
    headline = models.CharField(max_length=255)
    modified = models.DateField()
    _id = models.ObjectIdField()

    def __str__(self):
        return self.headline
