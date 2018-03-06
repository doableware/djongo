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
SQL prevents the usage of embedded objects in your models without serialization. With MongoDB as your Django backend, embed any other model into your parent model and save it as an [embedded document](https://docs.mongodb.com/manual/core/data-model-design/#data-modeling-embedding) into MongoDB

You should use embedded models when it does not make sense to store a data set as another table in the database and refer to it every time with a foreign key lookup. However, you still want to group the data set inside a separate model in python, as you wish to isolate it is functionality.

In case you don't plan on using your embedded model as a standalone model (which means it will always be embedded inside a parent model) you should add the `class Meta` and `abstract = True` This way Djongo will never register this model as an [actual model](https://docs.djangoproject.com/en/dev/topics/db/models/#abstract-base-classes).

It is a good practice to **define embedded models as abstract models** and this is **strongly recommended**.

### Parameters

Argument | Type | Description
---------|------|-------------
`model_container`| `models.Model` | The child model class type (not instance) that this embedded field will contain.
`model_form_class` | `models.forms.ModelForm` | The child model form class type of the embedded model.
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


class Entry(models.Model):
    blog = models.EmbeddedModelField(
        model_container=Blog,
        model_form_class=BlogForm
    )
    
    headline = models.CharField(max_length=255)    
    objects = models.DjongoManager()
```

## Embedded Form

While creating a Form from [the ModelForm](https://docs.djangoproject.com/en/dev/topics/forms/modelforms/), the embedded forms **get automatically generated** if the Model contains an embedded model inside it. Multiple embedded forms get automatically generated when the Model contains an array of embedded models.

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