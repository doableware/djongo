from djongo import models
from djongo.models import forms


class ReferenceBlog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()

    class Meta:
        abstract = True


class BlogForm(forms.ModelForm):

    class Meta:
        model = ReferenceBlog
        fields = (
            'name', 'tagline'
        )


class ReferenceMetaData(models.Model):
    pub_date = models.DateField()
    mod_date = models.DateField()
    n_pingbacks = models.IntegerField()
    rating = models.IntegerField()

    class Meta:
        abstract = True


class MetaDataForm(forms.ModelForm):

    class Meta:
        model = ReferenceMetaData
        fields = (
            'pub_date', 'mod_date',
            'n_pingbacks', 'rating'
        )


class ReferenceAuthor(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    _id = models.ObjectIdField()
    i = models.IntegerField()

    def __str__(self):
        return self.name


class AuthorForm(forms.ModelForm):

    class Meta:
        model = ReferenceAuthor
        fields = (
            'name', 'email'
        )


class ReferenceEntry(models.Model):
    # blog = models.EmbeddedModelField(
    #     model_container=ArrayBlog,
    #     model_form_class=BlogForm
    # )
    # meta_data = models.EmbeddedModelField(
    #     model_container=ArrayMetaData,
    #     model_form_class=MetaDataForm
    # )
    _id = models.ObjectIdField()
    headline = models.CharField(max_length=255)
    # body_text = models.TextField()

    authors = models.ArrayReferenceField(ReferenceAuthor, models.CASCADE )
    # n_comments = models.IntegerField()

    def __str__(self):
        return self.headline

