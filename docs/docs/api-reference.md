---
title: API Reference
permalink: /api-reference/
---


## The Embedded Model
 
SQL prevents the usage of embedded objects in your models without serialization. With MongoDB as your Django backend, embed any other model into your parent model and save it as an [embedded document](https://docs.mongodb.com/manual/core/data-model-design/#data-modeling-embedding) into MongoDB

Define the model to embed into parent model, like any Django model:

```python
from djongo import models

class BlogContent(models.Model):
    comment = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    class Meta:
        abstract = True
```

In case you don't plan on using your embedded model as a standalone model (which means it will always be embedded inside a parent model) you should add the `class Meta` and `abstract = True` as shown above. This way Djongo will never register this model as an [actual model](https://docs.djangoproject.com/en/dev/topics/db/models/#abstract-base-classes).

It is always a good practice to **make embedded models as abstract models** and this is **strongly recommended**.

## EmbeddedModelField

Embed the above model inside the parent model by creating an `EmbeddedModelField`. The `EmbeddedModelField` is similar to other Django Fields (like the `CharField`.)

```python
class EmbeddedModelField(Field):
    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form_class: typing.Optional[Type[forms.ModelForm]]=None,
                 model_form_kwargs: typing.Optional[dict]=None,
                 *args, **kwargs):
```

### Parameters

  * `model_container: Type[models.Model]` The child model class type (not instance) that this embedded field will contain.
  * `model_form_class: Optional[Type[models.forms.ModelForm]]` The child model form class type of the embedded model.
  * `model_form_kwargs: Optional[dict]` The kwargs (if any) that must be passed to the embedded model form while instantiating it.
  
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

## Embedded Array

With MongoDB there can be an [array](https://docs.mongodb.com/manual/core/document/#arrays) of embedded documents inside the parent document. You can create an **embed array/list of models inside the parent model** and store it directly into MongoDB.

Define the model to embed into parent model, like any Django model:

```python
from djongo import models

class BlogContent(models.Model):
    comment = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    class Meta:
        abstract = True
```

## ArrayModelField

Create an array of the above child model inside the parent model by creating an `ArrayModelField`. The `ArrayModelField` is similar to other Django Fields (like the `CharField`.)

```python
class ArrayModelField(Field):
    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form_class: typing.Type[forms.ModelForm]=None,
                 model_form_kwargs_l: dict=None,
                 *args, **kwargs):
```

### Parameters

  * `model_container: Type[models.Model]` The child model class type (not instance) that this array field will contain.
  * `model_form_class: Optional[Type[models.forms.ModelForm]]` The child model form class type of the array model. All child models inside the array must be of the same type. Mixing different types of child models inside the embedded array is not supported.
  * `model_form_kwargs: Optional[dict]` The kwargs (if any) that must be passed to the embedded model form while instantiating it.
  
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

## Embedded Form

While creating a Form from [the ModelForm](https://docs.djangoproject.com/en/dev/topics/forms/modelforms/), the embedded forms **get automatically generated** if the Model contains an embedded model inside it.

Multiple embedded forms get automatically generated when the Model contains an array of embedded models.

## QuerySet API

**All queries supported by the Django ORM are also supported with Djongo.**

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

## Querying Embedded Array fields
