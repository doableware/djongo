from djongo import models
from djongo.models import forms


class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100)

    class Meta:
        abstract = True


class AuthorForm(forms.ModelForm):

    class Meta:
        model = Author
        fields = (
            'name', 'email'
        )


class BlogContent(models.Model):
    comment = models.CharField(max_length=100)
    author = models.EmbeddedModelField(
        model_container=Author,
        model_form_class=AuthorForm
    )
    class Meta:
        abstract = True


class BlogContentSimple(models.Model):
    comment = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    class Meta:
        abstract = True


class BlogContentForm(forms.ModelForm):

    class Meta:
        model = BlogContentSimple
        fields = (
            'comment', 'author'
        )


class BlogPost(models.Model):
    h1 = models.CharField(max_length=100)
    content = models.EmbeddedModelField(
        model_container=BlogContentSimple,
        model_form_class=BlogContentForm
    )

    objects = models.DjongoManager()


class MultipleBlogPosts(models.Model):
    h1 = models.CharField(max_length=100)
    content = models.ArrayModelField(
        model_container=BlogContentSimple,
        model_form_class=BlogContentForm
    )

    objects = models.DjongoManager()

