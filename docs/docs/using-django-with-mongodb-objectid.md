---
title: Using Django with MongoDB ObjectID
permalink: "/using-django-with-mongodb-objectid/"
ready: false

---

The official [Django documentation](https://docs.djangoproject.com/en/2.0/topics/db/queries/) exemplifies 3 models that interact with each other: **Blog, Author and Entry**. This tutorial will consider the same models.

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

The blog `ForeignKey` of the `Entry` model was optimized in the [other tutorial](/djongo/integrating-django-with-mongodb/), here we optimize the authors `ManyToManyField`. A `ManyToManyField` defines a relation wherein an entry is related to several authors. It also defines a relation wherein an author could have made several entries. Django handles this internally by **creating another table**, the `entry_authors` table which contains mapping between different `entry_id` and `author_id`. 

Fetching the complete entry in this fashion will require 2 SQL queries. With the second query resulting in a JOIN. 

## Array Model Field
