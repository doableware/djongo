---
title: Using Djongo Array Model Field
permalink: /using-django-with-mongodb-array-field/
---

The official [Django documentation](https://docs.djangoproject.com/en/2.0/topics/db/queries/) exemplifies 3 models that interact with each other: **Blog, Author and Entry**. This tutorial considers the same 3 models. The `blog`; `ForeignKey` of the `Entry` model was optimized in the [other tutorial](/djongo/using-django-with-mongodb-data-fields/), here we optimize the `authors`; `ManyToManyField`.

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

 A `ManyToManyField` defines a relation wherein *an entry is made by several authors*. It also defines a relation wherein *an author could have made several entries*. Django handles this internally by **creating another table**, the `entry_authors` table which contains different mappings between  `entry_id` and `author_id`.

Fetching an entry will require 2 SQL queries. The second query will be an expensive JOIN query across `entry_authors` and `authors`. The Model described above will work perfectly well on MongoDB as well, when you use Djongo as the connector. MongoDB however offers much more powerful ways to make such queries. These queries come at the cost of higher disk space utilization.

As a designer using Djongo, you have the freedom to continue with the above schema. Alternatively, you can define a schema having a trade off on disk space for higher performance.

## Array Model Field

Let us redefine the `authors` in the `Entry` models using the `ArrayModelField`:

```python
from djongo import models

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

    class Meta:
        abstract = True
        
    def __str__(self):
        return self.name

class Entry(models.Model):
    blog = models.EmbeddedModelField(
        model_container=Blog,
    )
    meta_data = models.EmbeddedModelField(
        model_container=MetaData,
    )

    headline = models.CharField(max_length=255)
    body_text = models.TextField()

    authors = models.ArrayModelField(
        model_container=Author,
    )
    n_comments = models.IntegerField()

    def __str__(self):
        return self.headline

```

**Notice** how the `ManyToManyField` is now replaced by the `ArrayModelField`. To display the Array field in Django Admin, a `Form` for the field must be present. Since the array is made up of abstract `Author` models, the form can be easily created by using a `ModelForm`.  If you do not specify a `ModelForm` for your array  models in the `model_form_class` argument, Djongo will automatically generate a `ModelForm` for you.

### Django Admin

![Array-model-field](/djongo/assets/images/array-model-field.png)

> Django Admin reveals multiple neatly nested `Name` and `Email` fields under a single Author label.

Retrieving an entry from the database will result in **no JOINS and only a single database lookup. It is super fast**   

### Querying Array fields

Djongo uses a mixture of Django query syntax and MongoDB query syntax. Consider a query to retrieve all entries made by the author *Paul*. Using `ManyToManyField` this requires 2 SQL queries. First selects the `id` for author Paul from the `author` table. Next, a JOIN with `entry_authors` and `entry` gives the corresponding entries. 
 
With `ArrayModelField` the query reduces to a single simple query:   

```python
entries = Entry.objects.filter(authors={'name': 'Paul'})
```

Djongo lets you get even more specific with your queries. To query all entries where the third author is *Paul*:

```python
entries = Entry.objects.filter(authors={'2.name': 'Paul'})
```
Note: In MongoDB the first element in the array starts at index 0.

### Creating Array fields

A Model having an Array field can be created as follows:

```python
entry = Entry()
entry.authors = [Author()]
```


