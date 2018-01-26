---
title: Embedded Model Field
permalink: "/embedded-model-field/"
---
## The Embedded Model
 
SQL prevents the usage of embedded objects in your models without serialization. With MongoDB as your Django backend, embed any other model into your parent model and save it as an [embedded document](https://docs.mongodb.com/manual/core/data-model-design/#data-modeling-embedding) into MongoDB

In case you don't plan on using your embedded model as a standalone model (which means it will always be embedded inside a parent model) you should add the `class Meta` and `abstract = True` as shown above. This way Djongo will never register this model as an [actual model](https://docs.djangoproject.com/en/dev/topics/db/models/#abstract-base-classes).

It is always a good practice to **make embedded models as abstract models** and this is **strongly recommended**.

## EmbeddedModelField

```python
class EmbeddedModelField(Field):
    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form_class: typing.Optional[Type[forms.ModelForm]]=None,
                 model_form_kwargs: typing.Optional[dict]=None,
                 *args, **kwargs):
```

### Parameters

Argument | Type | Description
---------|------|-------------
`model_container`| `models.Model` | The child model class type (not instance) that this embedded field will contain.
`model_form_class` | `models.forms.ModelForm` | The child model form class type of the embedded model.
`model_form_kwargs` | `dict()` | The kwargs (if any) that must be passed to the embedded model form while instantiating it.
  
### Example

```python
class BlogContentForm(forms.ModelForm):
    class Meta:
        model = BlogContent
        fields = (
            'comment', 'author'
        )


class BlogContent(models.Model):
    comment = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    class Meta:
        abstract = True
        

class BlogPost(models.Model):
    h1 = models.CharField(max_length=100)
    content = models.EmbeddedModelField(
        model_container=BlogContent,
        model_form_class=BlogContentForm
    )
    
    objects = models.DjongoManager()
```

## Embedded Form

While creating a Form from [the ModelForm](https://docs.djangoproject.com/en/dev/topics/forms/modelforms/), the embedded forms **get automatically generated** if the Model contains an embedded model inside it.

Multiple embedded forms get automatically generated when the Model contains an array of embedded models.

## Querying Embedded fields

In the above example to query all BlogPost with content made by authors whose name startswith 'Paul'  use the following query:

```python
entries = BlogPost.objects.filter(content__startswith={'author': 'Paul'})
```

Internally Djongo converts this query (for BlogPost collection) to the form:

```python
filter = {
    'content.author': {
        '$regex': '^Paul.*$'
    }
}
```