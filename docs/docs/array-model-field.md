---
title: Array Model Field Reference
permalink: "/array-model-field/"
---

## ArrayModelField

```python
class ArrayModelField(Field):
    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form_class: typing.Type[forms.ModelForm]=None,
                 model_form_kwargs_l: dict=None,
                 *args, **kwargs):
```
With MongoDB there can be an [array](https://docs.mongodb.com/manual/core/document/#arrays) of embedded documents inside the parent document. You can create an **embed array/list of models inside the parent model** and store it directly into MongoDB.

### Parameters


Argument | Type | Description
---------|------|-------------
`model_container` | `models.Model` | The child model class type (not the instance) that this array field will contain.
`model_form_class` | `models.forms.ModelForm` | The child model form class type of the array model. All child models inside the array must be of the same type. Mixing different types of child models inside the embedded array is not supported.
`model_form_kwargs` | `dict()` | The kwargs (if any) that must be passed to the embedded model form while instantiating it.
  
### Example

```python
from djongo import models
from djongo.models import forms

class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()

    class Meta:
        abstract = True

class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = (
            'comment', 'author'
        )

class Author(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    
    class Meta:
        abstract = True

class AuthorForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = (
            'name', 'email'
        )
        
class Entry(models.Model):
    blog = models.EmbeddedModelField(
        model_container=Blog,
        model_form_class=BlogForm
    )
    
    headline = models.CharField(max_length=255)    
    authors = models.ArrayModelField(
        model_container=Author,
        model_form_class=AuthorForm
    )
    
    objects = models.DjongoManager()
```
