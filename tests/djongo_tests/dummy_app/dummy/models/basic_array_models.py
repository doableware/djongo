from djongo import models
from django import forms


class ArrayBlog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()

    class Meta:
        abstract = True


# class BlogForm(forms.ModelForm):
#
#     class Meta:
#         model = ArrayBlog
#         fields = (
#             'name', 'tagline'
#         )


class ArrayMetaData(models.Model):
    pub_date = models.DateField()
    mod_date = models.DateField()
    n_pingbacks = models.IntegerField()
    rating = models.IntegerField()

    class Meta:
        abstract = True


# class MetaDataForm(forms.ModelForm):
#
#     class Meta:
#         model = ArrayMetaData
#         fields = (
#             'pub_date', 'mod_date',
#             'n_pingbacks', 'rating'
#         )


class ArrayAuthor(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class AuthorForm(forms.ModelForm):

    class Meta:
        model = ArrayAuthor
        fields = (
            'name', 'email'
        )


class ArrayEntry(models.Model):
    # blog = models.EmbeddedModelField(
    #     model_container=ArrayBlog,
    #     model_form_class=BlogForm
    # )
    # meta_data = models.EmbeddedModelField(
    #     model_container=ArrayMetaData,
    #     model_form_class=MetaDataForm
    # )

    headline = models.CharField(max_length=255)
    # body_text = models.TextField()

    authors = models.ArrayModelField(
        model_container=ArrayAuthor,
        model_form_class=AuthorForm
    )
    # n_comments = models.IntegerField()

    def __str__(self):
        return self.headline

