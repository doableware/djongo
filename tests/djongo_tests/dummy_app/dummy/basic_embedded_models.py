from djongo import models
from django import forms


class EBlog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()

    class Meta:
        abstract = True

class BlogForm(forms.ModelForm):

    class Meta:
        model = EBlog
        fields = (
            'name', 'tagline'
        )

class MetaData(models.Model):
    pub_date = models.DateField()
    mod_date = models.DateField()
    n_pingbacks = models.IntegerField()
    rating = models.IntegerField()

    class Meta:
        abstract = True

class MetaDataForm(forms.ModelForm):

    class Meta:
        model = MetaData
        fields = (
            'pub_date', 'mod_date',
            'n_pingbacks', 'rating'
        )

class EAuthor(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()

    def __str__(self):
        return self.name

class EEntry(models.Model):
    blog = models.EmbeddedModelField(
        model_container=EBlog,
        model_form_class=BlogForm
    )
    # meta_data = models.EmbeddedModelField(
    #     model_container=MetaData,
    #     model_form_class=MetaDataForm
    # )

    headline = models.CharField(max_length=255)
    # body_text = models.TextField()

    # authors = models.ManyToManyField(EAuthor)
    # n_comments = models.IntegerField()

    def __str__(self):
        return self.headline

