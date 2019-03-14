---
title: Embedded Model Field Reference
permalink: "/embedded-model-field/"
---

## EmbeddedModelField

```python
class EmbeddedModelField(Field):
    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form_class: typing.Optional[Type[forms.ModelForm]]=None,
                 model_form_kwargs: typing.Optional[dict]=None,
                 *args, **kwargs):
```
Using MongoDB as your Django backend, you can embed any other model into your parent model and save it as an [embedded document](https://docs.mongodb.com/manual/core/data-model-design/#data-modeling-embedding).


### Parameters

Argument | Type | Description
---------|------|-------------
`model_container`| `models.Model` | The child model class type (not instance) that this embedded field will contain.
`model_form_class` | `models.forms.ModelForm` | The child model form class type of the embedded model.
`model_form_kwargs` | `dict()` | The kwargs (if any) that must be passed to the embedded model form while instantiating it.
  
### Example

```python
from djongo import models
from django import forms

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


class Entry(models.Model):
    blog = models.EmbeddedModelField(
        model_container=Blog,
        model_form_class=BlogForm
    )
    
    headline = models.CharField(max_length=255)    
    objects = models.DjongoManager()
```

## Embedded Form

While creating a Form from [the ModelForm](https://docs.djangoproject.com/en/dev/topics/forms/modelforms/), the embedded forms **get automatically generated** if the Model contains an embedded model inside it. Multiple embedded forms get automatically generated when the Model contains an array of embedded models. However, you can still override this by specifying the `model_form_class` argument in the EmbeddedModelField.

## Querying Embedded fields

In the above example to query all BlogPost with content made by authors whose name startswith *Beatles*  use the following query:

```python
entries = Entry.objects.filter(blog__startswith={'name': 'Beatles'})
```

Internally Djongo converts this query (for BlogPost collection) to the form:

```python
filter = {
    'blog.name': {
        '$regex': '^Beatles.*$'
    }
}
```