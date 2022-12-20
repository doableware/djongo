---
title: Using GridFSStorage
permalink: /using-django-with-mongodb-gridfs/
layout: docs
---

[GridFS](https://docs.mongodb.com/manual/core/gridfs/) is a specification for storing and retrieving files that exceed the [BSON-document](https://docs.mongodb.com/manual/reference/glossary/#term-bson) [size limit](https://docs.mongodb.com/manual/reference/limits/#limit-bson-document-size) of 16 MB.

GridFSStorage backend for Djongo aims to add a GridFS storage to upload files to using Django's file fields.

We first define our basic models. In the tutorials, we use the example used in the official [Django documentation](https://docs.djangoproject.com/en/2.0/topics/db/queries/). The documentation talks about 3 models that interact with each other: **Blog, Author and Entry**. To make the example clearer, few fields from the original models are omitted.

```python
## models.py
from djongo import models


class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()

    def __str__(self):
        return self.name

class Author(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    avatar = models.ImageField(upload_to='authors')

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
    featured_image = models.ImageField(upload_to='entries')

    def __str__(self):
        return self.headline
```

### GridFS Storage

The `Author` and `Entry` models define a field type `ImageField`. Until now, when you upload files, those files will be uploaded to `MEDIA_ROOT/authors` and `MEDIA_ROOT/entries` directories.

So, what happens if you want to save those files into database? That is when appears GridFS to the rescue!. 

In your `models.py` file you could probably do:

```python
## models.py
from django.conf import settings

# Add the import for GridFSStorage
from djongo.storage import GridFSStorage


# Define your GrifFSStorage instance 
grid_fs_storage = GridFSStorage(collection='myfiles', base_url=''.join([settings.BASE_URL, 'myfiles/']))
```

In `Author` change `avatar` field definition for this:

```python
avatar = models.ImageField(upload_to='authors', storage=grid_fs_storage)
```

In `Entry` change `avatar` field definition for this:

```python
featured_image = models.ImageField(upload_to='entries', storage=grid_fs_storage)
```

And, that's all, when you upload `avatar` for `Author` it will be saved in collection `myfiles.authors.files` or when you upload `featured_image` for `Entry` it will be saved in collection `myfiles.entries.files`


### Retriving values

Suppose that you have saved some documents in your collection related to Author model, so if you want to retrieve one of them, you could probably do: 
 
```
# in a python console 
>>> author = Author.object.get(id=1)
>>> print(author)
{ 'id': 1, 'name': 'Lisa Stoner', 'email': 'lisa.stoner@nomail.local', 'avatar': 'http://mysite.local/myfiles/5dc880e06a8e6a7effa592a7'}
```

As you can see, the value that is retrieved in `avatar` field is the `_id` related to the saved image|file. In this case you get a url because you probably have in your settings file the following:
```python
UPLOADED_FILES_USE_URL = True
```