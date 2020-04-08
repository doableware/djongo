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
    name = models.CharField(max_length=200)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class BasicBlog(NamedBlog):
    tagline = models.TextField()


class BasicAuthor(NamedAuthor):
    pass


class BasicHeadlinedEntry(models.Model):
    headline = models.CharField(max_length=255)

    class Meta:
        abstract = True

    def __str__(self):
        return self.headline


class BasicRelatedEntry(BasicHeadlinedEntry):
    blog = models.ForeignKey(BasicBlog, on_delete=models.CASCADE)
    authors = models.ManyToManyField(BasicAuthor)
