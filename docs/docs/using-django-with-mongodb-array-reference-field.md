---
title: Using Djongo Array Reference Field
permalink: /using-django-with-mongodb-array-reference-field/
---

## Array Reference field

The `ArrayReferenceField` is one of the most powerful features of Djongo. The `ArrayModelField` stores the embedded models within a MongoDB array as embedded documents for each entry. If entries contain duplicate embedded documents, using the `ArrayModelField` would require unnecessary disk space. The `ManyToManyField` on the other hand has a separate table for all the entries. In addition, it also creates an intermediate "through/join" table which records all the mappings.

The `ArrayReferenceField` is a bargain between the `ArrayModelField` and `ManyToManyField`. A separate collection is used for storing all entries (instead of embedding it as an array). This means there is no data duplication. However, the intermediate "through/join" mapping table is completely skipped! This is achieved by storing only a reference to the entries in the embedded array.

While the `ManyToManyField` required two queries to fetch data, the `ArrayReferenceField` requires just one query. If you have used the `ManyToManyField`, then you know how to use the `ArrayReferenceField`. In fact **it implements the exact same API** as the `ManyToManyField`.

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
 
 The `ArrayReferenceField` behaves exactly like the `ManyToManyField`. However, underneath only references to the entries are being stored in the array.
 


