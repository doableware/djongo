from djongo import models


class EmbeddedBlog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class EmbeddedEntry(models.Model):
    blog = models.EmbeddedModelField(
        model_container=EmbeddedBlog
    )
    headline = models.CharField(max_length=255)

    def __str__(self):
        return self.headline

