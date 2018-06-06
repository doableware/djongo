from djongo import models


class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()

    def __str__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Entry(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    headline = models.CharField(max_length=255)
    authors = models.ManyToManyField(Author)

    def __str__(self):
        return self.headline