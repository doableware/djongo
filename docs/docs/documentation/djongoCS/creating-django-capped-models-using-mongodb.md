---
title: Creating Capped Models using MongoDB
permalink: /creating-django-capped-models-using-mongodb/
layout: server
---

[Capped collections][capped] are fixed-size collections that support high-throughput operations that insert and retrieve documents based on insertion order. Capped collections work in a way similar to circular buffers: once a collection fills its allocated space, it makes room for new documents by overwriting the oldest documents in the collection.

Djongo lets you define certain Models as 'Capped' Models. The `Entry` Model is a perfect candidate for being stored as a Capped Model.

```python
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
    
    class Meta:
        capped = True
        size = 5242880
        max = 5000
        
    def __str__(self):
        return self.headline

``` 

As most SQL DBs do not support capped tables, Django lacks a way to define such tables during a migration. Djongo comes with it is own version of `manage.py` to make this happen. Switch to the root directory of your app and from the command line run:

```
python -m djongo.manage migrate
```

This will result in all Models having `capped == True` to being recreated as Capped collections. Use this command only if such a collection doesn't already exists or is empty, as `djongo.manage` will drop all collections marked as capped in the model but are not capped in the DB and create a new empty capped collection.

{{page.notice.not_ready}}

[capped]: https://docs.mongodb.com/manual/core/capped-collections/