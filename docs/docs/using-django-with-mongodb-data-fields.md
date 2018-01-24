---
title: Using Django with MongoDB data fields
permalink: /using-django-with-mongodb-data-fields/
---


Django Admin is a powerful tool for managing data used in your app. If you are using MongoDB as your backend, Django Admin can be directly used to create NoSQL ‘embedded models’ using Djongo to boost your performance.

The Django admin application can use your models to automatically build a site area that you can use to create, view, update, and delete records. This can save you a lot of time during development, making it very easy to test your models and get a feel for whether you have the right data. Most of you already know about Django Admin, but to explain how it is used with Djongo, I will start with a simple example.

First we define our basic models. In this article, I will use the same models used in the official [Django documentation](https://docs.djangoproject.com/en/2.0/topics/db/queries/). The documentation talks about 3 models that interact with each other: **Blog, Author and Entry**. Some of the fields from the models have been omitted to make the example clearer.

```python
from djongo import models

class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()

    def __str__(self):
        return self.name

class Author(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()

    def __str__(self):
        return self.name

class Entry(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    headline = models.CharField(max_length=255)
    body_text = models.TextField()
    pub_date = models.DateField()
    mod_date = models.DateField()
    authors = models.ManyToManyField(Author)
    n_comments = models.IntegerField()
    n_pingbacks = models.IntegerField()
    rating = models.IntegerField()

    def __str__(self):
        return self.headline
```

You start with your admin development by *registering* a model. Register the models defined above in the `admin.py` file.

```python
from django.contrib import admin
from .models import Blog, Author, Entry

admin.site.register(Blog)
admin.site.register(Author)
admin.site.register(Entry)
```

## Data Model

The `Entry` model defined in the documentation consists of 3 parts:
* 1-to-Many Relationship: ‘A `Blog` is made up of multiple `Entry`s’ and ‘each `Entry` is associated with just *one* `Blog`’. The same entry can’t appear in two Blogs and this defines the 1-to-Many relationship.
* Many-to-Many Relationship: ‘An `Entry` can have *multiple* `Author`s’ and ‘an `Author` can make multiple `Entry`s’. This defines the many-to-many relationship for our data model.
* Normal data columns

**An interesting point of note** is that the `Blog` model consists of just 2 fields. Most of the data is stored in the `Entry` model.

So what happens when a user enters your blog? A user wants to view the ‘Beatles blog’. In your project you could probably do:

```python
blog = Blog.objects.get(name='Beatles Blog')
```
Next, to retrieve all entries related to the Beatles blog, follow it up with:

```python
entries = Entry.objects.filter(blog_id=blog.id)
```

While it is alright to obtain entries in this fashion, you end up **making 2 trips** to the database. If you are using a SQL based backend this is not the most efficient way. The number of trips can be reduced to one. Django makes the query more efficient:

```python
entries = Entry.objects.filter(blog__name='Beatles Blog')
```

This query will hit the database just once. All entries associated with a `Blog` having the name ‘Beatles Blog’ will be retrieved. However, this query generates a SQL JOIN. **JOINs are much slower when compared to a single table lookup**.

Since a `Blog` model shares a 1-to-many relationship with `Entry` I can rewrite my `Entry` model:

```python
class Entry(models.Model):
    blog_name = models.CharField(max_length=100)
    blog_tagline = models.TextField()
    headline = models.CharField(max_length=255)
    body_text = models.TextField()
    pub_date = models.DateField()
    mod_date = models.DateField()
    authors = models.ManyToManyField(Author)
    n_comments = models.IntegerField()
    n_pingbacks = models.IntegerField()
    rating = models.IntegerField()

    def __str__(self):
        return self.headline
```

I have inserted the `Blog` fields into the `Entry` model. With this new data model the query changes to:

```python
entries = Entry.objects.filter(blog_name='Beatles Blog')
```

There are no JOINs generated with this and queries will be much faster. I know what you are thinking though, aren't we duplicating data? Yes we are, but only if the backend database doesn’t use data compression.

OK, so use compression to mitigate data duplication but take a look at our Entry model, it has 10 columns and is getting unmanageable.

## The Embedded Model

A hierarchical structure to *Nature* is apparent. Electrons and protons add up to make atoms, which make molecules, that combine to form proteins, which make cells (and you know the rest).. There is hierarchy to *data* too.

A `Blog` contains a `name` and a `tagline`. An `Entry` contains details of the `Blog`, the `Authors`, `body_text` and some `Meta` data. To make the `Entry` model manageable I will redefine it.

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

class Author(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()

    def __str__(self):
        return self.name

class Entry(models.Model):
    blog = models.EmbeddedModelField(
        model_container=Blog,
        model_form_class=BlogForm
    )
    meta_data = models.EmbeddedModelField(
        model_container=MetaData,
        model_form_class=MetaDataForm
    )

    headline = models.CharField(max_length=255)
    body_text = models.TextField()

    authors = models.ManyToManyField(Author)
    n_comments = models.IntegerField()

    def __str__(self):
        return self.headline
```

Register the new models in `admin.py`.

```python
from django.contrib import admin
from .embedded_models import Author, Entry

admin.site.register(Author)
admin.site.register(Entry)
```

The number of fields in `Entry` model is reduce to 6. I fire up Django Admin to check what is up!

<div style="max-width: 100%; margin-left: auto; margin-right: auto">
    <img src="/djongo/assets/images/embedded-admin.png" alt="Django Admin">
</div>


Only the `Entry` and `Author` model are registered. I click on *Entrys Add* and get:

<div style="max-width: 100%; margin-left: auto; margin-right: auto">
    <img src="/djongo/assets/images/embedded-addentry.png" alt="Django Admin">
</div>

The `Name` and `Tagline` fields are neatly nested within Blog. `Pub date` `Mod date` `N pingbanks` and `Rating` are neatly nested within Meta data.

<div style="max-width: 100%; margin-left: auto; margin-right: auto">
    <img src="/djongo/assets/images/embedded-nested.png" alt="Django Admin">
</div>


When a user queries for a blog named ‘Beatles Blog’ the query for filtering an embedded model now changes to:

```python
entries = Entry.objects.filter(blog={'name': 'Beatles Blog'})
```

This query will return all entries having an embedded blog with the name ‘Beatles Blog’. **The query will hit the database just once and there are no JOINs involved. It’s super fast.**



## API Reference

### The Embedded Model
 
SQL prevents the usage of embedded objects in your models without serialization. <b>Not anymore.</b> With mongoDB as your django backend, embed any other model into your parent model and save it as an [embedded document](https://docs.mongodb.com/manual/core/data-model-design/#data-modeling-embedding) into mongoDB

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

#### EmbeddedModelField

Embed the above model inside the parent model by creating an `EmbeddedModelField`. The `EmbeddedModelField` is similar to other Django Fields (like the `CharField`.)

```python
class EmbeddedModelField(Field):
    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form_class: typing.Optional[Type[forms.ModelForm]]=None,
                 model_form_kwargs: typing.Optional[dict]=None,
                 *args, **kwargs):
```

##### Parameters

  * `model_container: Type[models.Model]` The child model class type (not instance) that this embedded field will contain.
  * `model_form_class: Optional[Type[models.forms.ModelForm]]` The child model form class type of the embedded model.
  * `model_form_kwargs: Optional[dict]` The kwargs (if any) that must be passed to the embedded model form while instantiating it.
  
##### Example

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

### Embedded Array

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

#### ArrayModelField

Create an array of the above child model inside the parent model by creating an `ArrayModelField`. The `ArrayModelField` is similar to other Django Fields (like the `CharField`.)

```python
class ArrayModelField(Field):
    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form_class: typing.Type[forms.ModelForm]=None,
                 model_form_kwargs_l: dict=None,
                 *args, **kwargs):
```

##### Parameters

  * `model_container: Type[models.Model]` The child model class type (not instance) that this array field will contain.
  * `model_form_class: Optional[Type[models.forms.ModelForm]]` The child model form class type of the array model. All child models inside the array must be of the same type. Mixing different types of child models inside the embedded array is not supported.
  * `model_form_kwargs: Optional[dict]` The kwargs (if any) that must be passed to the embedded model form while instantiating it.
  
##### Example

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

### Embedded Form

While creating a Form from [the ModelForm](https://docs.djangoproject.com/en/dev/topics/forms/modelforms/), the embedded forms **get automatically generated** if the Model contains an embedded model inside it.

Multiple embedded forms get automatically generated when the Model contains an array of embedded models.

### QuerySet API

**All queries supported by the Django ORM are also supported with Djongo.**

#### Querying Embedded fields

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

#### Querying Embedded Array fields

<script>
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-75159067-1', 'auto');
  ga('send', 'pageview');

</script>