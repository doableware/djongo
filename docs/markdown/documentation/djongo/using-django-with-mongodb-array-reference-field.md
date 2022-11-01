---
title: Using Djongo Array Reference Field
permalink: /using-django-with-mongodb-array-reference-field/
layout: docs
---

## Array Reference field

The `ArrayField` stores embedded models within a MongoDB array as embedded documents for each entry. However, if entries contain duplicate embedded documents, using the `ArrayField` would result in unnecessary duplication and increased disk space usage. On the other hand, the Django `ManyToManyField`  only refers to a different table of entries. In addition however, it creates an intermediate "through/join" table which records all the mappings.

The `ArrayReferenceField` is one of the most powerful features of Djongo. The `ArrayReferenceField` is a bargain between the `ArrayField` and `ManyToManyField`. Similar to the `ManyToManyField` a separate collection is used for storing duplicate entries (instead of embedding them as an array). This means there is no data duplication. However, the intermediate "through/join" mapping table is completely skipped! This is achieved by storing only a reference to the entries in the embedded array.

While the `ManyToManyField` required two queries to fetch data, the `ArrayReferenceField` requires just one query and is much faster. If you have used the `ManyToManyField`, then you know how to use the `ArrayReferenceField`. In fact, **it implements the exact same API** as the `ManyToManyField`. You can replace all existing `ManyToManyField` with `ArrayReferenceField` and everything will continue to work as is.

In the example the `Entry` Model can be rewritten as follows:

```python
class Author(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()

    def __str__(self):
        return self.name
        
class Entry(models.Model):
    blog = models.EmbeddedField(
        model_container=Blog,
        model_form_class=BlogForm
    )
    meta_data = models.EmbeddedField(
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
 
 The `ArrayReferenceField` behaves exactly like the `ManyToManyField`. However, underneath only references to the entries are being stored in the array.
 
## ArrayReferenceField

```python
class ArrayReferenceField(ForeignKey):
    def __init__(self, *args, **kwargs):
```
### Arguments

Same as the `ForeignKey` Base class