---
title: Using Django with MongoDB Array Field
permalink: /using-django-with-mongodb-array-field/
ready: false
---

The official [Django documentation](https://docs.djangoproject.com/en/2.0/topics/db/queries/) exemplifies 3 models that interact with each other: **Blog, Author and Entry**. This tutorial considers the same 3 models.

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

The `blog` `ForeignKey` of the `Entry` model was optimized in the [other tutorial](/djongo/integrating-django-with-mongodb/), here we optimize the `authors` `ManyToManyField`. A `ManyToManyField` defines a relation wherein an entry is made by several authors. It also defines a relation wherein an author could have made several entries. Django handles this internally by **creating another table**, the `entry_authors` table which contains different mappings between  `entry_id` and `author_id`. 

Fetching an entry will require 2 SQL queries, with the second query being an expensive JOIN query across `entry_authors` and `authors`. The Model described above will work perfectly well on MongoDB as well when you use Djongo as the connector. MongoDB however offers much more powerful ways to make such queries. These queries come at the cost of higher disk space utilization. As a designer, using Djongo you have the freedom to continue with the above schema or define a schema requiring a trade off on disk space for higher performance.  

## Array Model Field

The `authors` in the `Entry` models can be redefined using the `ArrayModelField` as follows:

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

    class Meta:
        abstract = True
        
    def __str__(self):
        return self.name

class AuthorForm(forms.ModelForm):

    class Meta:
        model = Author
        fields = (
            'name', 'email'
        )

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

    authors = models.ArrayModelField(
        model_container=Author,
        model_form_class=AuthorForm,
    )
    n_comments = models.IntegerField()

    def __str__(self):
        return self.headline

```

**Notice** how the `ManyToManyField` is now replaced by the `ArrayModelField`. To display the Array field in Django Admin, a `Form` for the field must be present. Since the array is made up of abstract `Author` models, the form can be easily created by using a `ModelForm`.  The `AuthorForm` defines `Author` as the model with `name` and `email` as the form fields.

### Django Admin

![Array-model-field](/djongo/assets/images/array-model-field.png)

> Django Admin reveals multiple neatly nested `Name` and `Email` fields under a single Author label.

Retrieving an entry from the database will result in **no JOINS and only a single database lookup. It's super fast**   

### Querying Array fields

Djongo uses a mixture of Django query syntax and MongoDB query syntax. Consider a query to retrieve all entries made by the author *Paul*. Using `ManyToManyField` this requires 2 SQL queries. First selects the `id` for author Paul from the `author` table. Next, a JOIN with `entry_authors` and `entry` gives the corresponding entries. 
 
With `ArrayModelField` the query reduces to a single simple query:   

```python
entries = Entry.objects.filter(authors={'name': 'Paul'})
```

Djongo lets you get even more specific with your queries. To query all entries where the third author is *Paul*:

```python
entries = Entry.objects.filter(authors={'name.2': 'Paul'})
```
Note: In MongoDB the first element in the array starts at index 0.


## Array Reference field

The `ArrayModelField` stores the embedded models within a MongoDB array as embedded documents for each entry. If entries contain duplicate embedded documents, using the `ArrayModelField` would result in unnecessary disk utilization. Storing a reference to the embedded document instead of the entire document will save disk space.

In the example the `Entry` Model can be rewritten as follows:

```python
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

    authors = models.ArrayReferenceField(
        to=Author,
        on_delete=models.CASCADE,
    )
    n_comments = models.IntegerField()

    def __str__(self):
        return self.headline

``` 
**Notice** how the `Author` model is no longer set as `abstract`. This means a separate `author` collection will be created in the DB. Simply set the `authors` to a list containing several author instances. When the entry gets saved, only a reference to the primary_key of the author model is saved in the array. Upon retrieving an entry from the DB the corresponding authors are automatically looked up and the author list is populated.
 
 The `ArrayReferenceField` behaves similar to `ArrayModelField`. However, underneath only references are being stored instead of complete embedded documents. Doing this however comes at the cost of performance as internally MongoDB is doing a lookup across two collections.  
 
## List field 

`ArrayModelField` and `ArrayReferenceField` require all Models in the list to be of the same type. MongoDB allows the saving of arbitrary data inside it's embedded array. The `ListField` is useful in such cases. The list field cannot be represented in Django Admin though and can only be used in the python script.

