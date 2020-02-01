---
title: Using Djongo Model fields
permalink: /using-django-with-mongodb-data-fields/
---

## EmbeddedField

```python
class EmbeddedField(Field):
    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form_class: typing.Optional[Type[forms.ModelForm]]=None,
                 model_form_kwargs: typing.Optional[dict]=None,
                 *args, **kwargs):
```
MongoDB allows the creation of an [embedded document](https://docs.mongodb.com/manual/core/data-model-design/#data-modeling-embedding). By using Djongo as your connector, you can embed any other model into your parent model through the `EmbeddedField`. 


### Arguments

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

class Entry(models.Model):
    blog = models.EmbeddedField(
        model_container=Blog
    )
    
    headline = models.CharField(max_length=255)    
    objects = models.DjongoManager()
```

## Embedded Form

While creating a Form for [the ModelForm](https://docs.djangoproject.com/en/dev/topics/forms/modelforms/), the embedded forms **are automatically generated**. Multiple embedded forms get automatically generated when the Model contains an array of embedded models. However, you can still override this by specifying the `model_form_class` argument in the `EmbeddedField`.

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
            'name', 'tagline'
        )


class Entry(models.Model):
    blog = models.EmbeddedField(
        model_container=Blog,
        model_form_class=BlogForm
    )
    
    headline = models.CharField(max_length=255)    
    objects = models.DjongoManager()
```

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

## Using EmbeddedField in Django Admin
 
Django Admin is a powerful tool for managing data used in your app. When your models use Djongo relational fields,  you can create NoSQL "embedded models" directly from the Django Admin. **These fields provide better performance when compared with traditional Django relational fields.**

The Django admin application can use your models to automatically build a site area that you can use to create, view, update, and delete records. This can save you a lot of time during development, making it very easy to test your models and get a feel for whether you have the right data. Most of you already know about Django Admin, but to demonstrate how to use it with Djongo, we start with a simple example. You can ask for [expert support](https://www.patreon.com/nesdis) if your project uses complex models.

We first define our basic models. In the tutorials, we use the example used in the official [Django documentation](https://docs.djangoproject.com/en/2.0/topics/db/queries/). The documentation talks about 3 models that interact with each other: **Blog, Author and Entry**. To make the example clearer, few fields from the original models are omitted. 

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

admin.site.register([Blog, Author, Entry])
```

## Data Model

The `Entry` model defined in the documentation consists of 3 parts:
* 1-to-Many Relationship: A `Blog` is made up of multiple `Entry`s’ and each `Entry` is associated with just *one* `Blog`. The same entry cannot appear in two `Blog`s’ and this defines the 1-to-Many relationship.
* Many-to-Many Relationship: An `Entry` can have *multiple* `Author`s’ and an `Author` can make multiple `Entry`s’. This defines the many-to-many relationship for our data model.
* Normal data columns.

**An interesting point of note** is that the `Blog` model consists of just 2 fields. Most of the data is stored in the `Entry` model.

So what happens when a user enters your blog? A user wants to view the ‘Beatles blog’. In your project you could probably do:

```python
blog = Blog.objects.get(name='Beatles Blog')
```

Next, to retrieve all entries related to the Beatles blog, follow it up with:

```python
entries = Entry.objects.filter(blog_id=blog.id)
```

While it is fine to obtain entries in this fashion, you end up **making 2 trips** to the database. If you are using a SQL based backend this is not the most efficient way. The number of trips can be reduced to one. Django makes the query more efficient:

```python
entries = Entry.objects.filter(blog__name='Beatles Blog')
```

This query will hit the database just once. All entries associated with a `Blog` having the name ‘Beatles Blog’ will be retrieved. However, this query generates a SQL JOIN. **JOINs are much slower when compared to single table lookups**.

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

There are no JOINs generated with this and queries will be much faster. What you are thinking though is, are we  not duplicating data? Yes we are, but only if the backend database does not use data compression.

Using compression to mitigate data duplication is fine but take a look at our Entry model, it has 10 columns and is getting unmanageable.

## The Embedded Model

The hierarchical structure in *Nature* is apparent. For example,  electrons and protons add up to make atoms, which make molecules. There is hierarchy to *data* too.

A `Blog` contains a `name` and a `tagline`. An `Entry` contains details of the `Blog`, the `Authors`, `body_text` and some `Meta` data. To make the `Entry` model manageable let us redefine it:

You should use embedded models when it does not make sense to store a data set as another table in the database and refer to it every time with a foreign key lookup. However, you still want to group the data set in a hierarchical fashion, to isolate its functionality.

In case you don't plan on using your embedded model as a standalone model (which means it will always be embedded inside a parent model) you should add the `class Meta` and `abstract = True` This way Djongo will never register this model as an [actual model](https://docs.djangoproject.com/en/dev/topics/db/models/#abstract-base-classes).

It is a good practice to **define embedded models as abstract models** and this is **strongly recommended**.

```python
from djongo import models
from django import forms

class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()

    class Meta:
        abstract = True

class MetaData(models.Model):
    pub_date = models.DateField()
    mod_date = models.DateField()
    n_pingbacks = models.IntegerField()
    rating = models.IntegerField()

    class Meta:
        abstract = True

class Author(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()

    def __str__(self):
        return self.name

class Entry(models.Model):
    blog = models.EmbeddedField(
        model_container=Blog,
    )
    meta_data = models.EmbeddedField(
        model_container=MetaData,
    )

    headline = models.CharField(max_length=255)
    body_text = models.TextField()
    authors = models.ManyToManyField(Author)
    n_comments = models.IntegerField()

    def __str__(self):
        return self.headline
```

To display the embedded models in Django Admin, a `Form` for the embedded fields is required. Since the embedded field is an abstract model, the form for it can be easily created by using a `ModelForm`. The `BlogForm` defines `Blog` as the model with `name` and `tagline` as the form fields. 

If you do not specify a `ModelForm` for your embedded models, and pass it using the `model_form_class` argument, Djongo will automatically generate a `ModelForm` for you.

Register the new models in `admin.py`. 

```python
from django.contrib import admin
from .embedded_models import Author, Entry

admin.site.register([Author, Entry])
```

The number of fields in the `Entry` model is reduce to 6. Fire up Django Admin to check what is up!
 
![Django Admin](/djongo/assets/images/embedded-admin.png)

Only the `Entry` and `Author` model are registered. I click on *Entrys Add* and get:

![Django Admin](/djongo/assets/images/embedded-nested.png)


> The `Name` and `Tagline` fields are neatly nested within Blog. `Pub date` `Mod date` `N pingbanks` and `Rating` are neatly nested within Meta data.

When a user queries for a blog named ‘Beatles Blog’, the query for filtering an embedded model changes to:

```python
entries = Entry.objects.filter(blog={'name': 'Beatles Blog'})
```

This query will return all entries having an embedded blog with the name ‘Beatles Blog’. **The query will hit the database just once and there are no JOINs involved.**

