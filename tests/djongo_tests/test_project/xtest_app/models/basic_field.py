from djongo import models


class Entry(models.Model):
    _id = models.ObjectIdField()

    class Meta:
        abstract = True


class HeadlinedEntry(Entry):
    headline = models.CharField(max_length=255)

    class Meta:
        abstract = True

    def __str__(self):
        return self.headline


class NamedBlog(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class NamedAuthor(models.Model):
    _id = models.ObjectIdField(primary_key=True)
    name = models.CharField(max_length=200)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class BasicBlog(NamedBlog):
    _id = models.AutoField(primary_key=True)
    tagline = models.TextField(default='##tagline##')


class BasicAuthor(NamedAuthor):
    _id = models.AutoField(primary_key=True)


class BasicHeadlinedEntry(models.Model):
    headline = models.CharField(max_length=255)

    class Meta:
        abstract = True

    def __str__(self):
        return self.headline


class BasicRelatedEntry(BasicHeadlinedEntry):
    _id = models.AutoField(primary_key=True)
    blog = models.ForeignKey(BasicBlog, on_delete=models.CASCADE)
    authors = models.ManyToManyField(BasicAuthor)


class EmbeddedFieldEntry(HeadlinedEntry):
    blog = models.EmbeddedField(
        model_container=NamedBlog
    )

    class Meta:
        abstract = True
