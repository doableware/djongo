---
title: Model Query
layout: server
permalink: /model-query/
---

## Text Search

Djongo lets you run [MongoDB text search](https://docs.mongodb.com/manual/core/text-search-operators/) queries on Django `CharField` and `TextField`. To run a text search, use the `text_search` operator that comes built in with Djongo.

### Example

```python
from djongo.models.indexes import TextIndex
from djongo import models

class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()

    class Meta:
        indexes = [
            TextIndex(fields=['name'])
        ]
```

```python
Blog.objects.filter(name__text_search='Paul Lennon')
```
This will generate the pymongo command:

```python
db.blog.find( { '$text': { '$search': "Paul Lennon" } } )
```

<!--
## Text Search using aggregation
-->

## Geospatial Queries

Geospatial queries are carried out in Djongo by using a combination of the `near` lookup operator and the `Near` search object. 

```python
class Near(
    type=None,
    coordinates=None,
    minDistance=None,
    maxDistance=None)
```
### Example

```python
from djongo.models.indexes import TwoDSphereIndex
from djongo import models

class Location(models.Model):
    type = models.CharField(max_length=100)
    coordinates = models.ArrayField()

    class Meta:
        abstract = True

class Entry(models.Model):
    loc = models.EmbeddedField(
        model_container=Location,
    )
    class Meta:
        indexes = [
            TwoDSphereIndex(fields=['loc'])
        ]
```

```python
from djongo.models import Near

search_region = Near(
    type='point',
    coordinates=[-33.9, 89.81],
    minDistance=100,
    maxDistance=200
)

Entry.objects.filter(loc__near=search_region)
```

This generates the following pymongo search query:

```python
db.entry.find({
     'loc': 
        { '$near':
          {
            '$geometry': { 'type': "Point",  'coordinates': [-33.9, 89.81] },
            '$minDistance': 100,
            '$maxDistance': 200
          }
        }
   })
```

## Specifying Query Options

Djongo lets you specify the configuration of the find command into your [QuerySets](https://docs.djangoproject.com/en/dev/ref/models/querysets/). Call the `configure` method on a QuerySet to configure the find query. All options supported by [aggregate](https://api.mongodb.com/python/current/api/pymongo/collection.html#pymongo.collection.Collection.aggregate) or [find](https://api.mongodb.com/python/current/api/pymongo/collection.html#pymongo.collection.Collection.find) can be included as `kwargs`. Example of valid arguments:

### Arguments

Argument | Type | Description
---------|------|-------------
`allowDiskUse` | `boolean` | Enables writing to temporary files
`collation` | `Collation` | Used to specify the [collation](https://docs.mongodb.com/manual/reference/collation/). Takes an instance of [Collation](https://api.mongodb.com/python/current/api/pymongo/collation.html)


### Example

```python
Blog.objects.filter(name='John Lennon').configure(hint=['-tagline'])
```
This generates the following pymongo find query:

```python
db.blog.find({'name': 'John Lennon'}, hint=[('tagline', pymongo.DESCENDING)])
```

## Tailable Cursors
Tailable cursors are used to retrieve data from [capped collections](https://docs.mongodb.com/manual/core/capped-collections/). The querySet first has to be configured using `configure` to use a tailable cursor in the pymongo find command. Results of the querySet can only be accessed by generating an iterator by calling the [QuerySet iterator](https://docs.djangoproject.com/en/3.0/ref/models/querysets/#iterator)  

### Example

```python
iterable = Blog.objects.filter(name='John').configure(cursor_type=CursorType.TAILABLE).iterator()
for blog in iterable:
    blog.name
```


