---
title: Array Model Field
permalink: "/array-model-field/"
---


## Embedded Array

With MongoDB there can be an [array](https://docs.mongodb.com/manual/core/document/#arrays) of embedded documents inside the parent document. You can create an **embed array/list of models inside the parent model** and store it directly into MongoDB.


## ArrayModelField

```python
class ArrayModelField(Field):
    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form_class: typing.Type[forms.ModelForm]=None,
                 model_form_kwargs_l: dict=None,
                 *args, **kwargs):
```

### Parameters


Argument | Type | Description
---------|------|-------------
`model_container` | `models.Model` | The child model class type (not the instance) that this array field will contain.
`model_form_class` | `models.forms.ModelForm` | The child model form class type of the array model. All child models inside the array must be of the same type. Mixing different types of child models inside the embedded array is not supported.
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
    content = models.ArrayModelField(
        model_container=BlogContent,
        model_form_class=BlogContentForm
    )
    
    objects = models.DjongoManager()
```
