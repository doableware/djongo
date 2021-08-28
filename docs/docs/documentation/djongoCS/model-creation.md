---
title: Model Creation
layout: server
permalink: /model-creation/
---


## Schema Validation and CheckConstraint 

Djongo automatically generates schema validation JSON documents for your models providing an extra layer of data validation and checking from within MongoDB. By creating [check constraints](https://docs.djangoproject.com/en/3.0/ref/models/constraints/#checkconstraint) in the Model Meta definition, djongo automatically interprets it to generate a [JSON Schema](https://docs.mongodb.com/manual/core/schema-validation/#json-schema) and a [query expression](https://docs.mongodb.com/manual/core/schema-validation/#other-query-expressions)

### Example

```python
from djongo.models import CheckConstraint, Q
from djongo import models
from pymongo.read_concern import ReadConcern

class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()
    author_age = models.IntegerField()

    class Meta:
        constraints = [
             CheckConstraint(check=Q(author_age__gte=18), name='age_gte_18')
        ]
```

## CollectionConstraint and Capped Collections
Djongo introduces a new `CollectionConstraint`. Use this to specify MongoDB specific collection properties that are usually used when calling [create_collection](https://api.mongodb.com/python/current/api/pymongo/database.html#pymongo.database.Database.create_collection)

```python
class CollectionConstraint(**kwargs)
```

All arguments passed to `create_collection` with the exception of `name` can be used to create the `CollectionConstraint` instance. Valid arguments include, but are not limited to those described below

### Arguments

Argument | Type | Description
---------|------|-------------
`codec_options` | `CodecOptions` | An instance of [CodecOptions](https://api.mongodb.com/python/current/api/bson/codec_options.html#bson.codec_options.CodecOptions).
`collation` | `Collation` | Takes an instance of [Collation](https://api.mongodb.com/python/current/api/pymongo/collation.html)

### Example

```python
from djongo.models import CollectionConstraint
from djongo import models
from pymongo.read_concern import ReadConcern

class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()

    class Meta:
        constraints = [
            CollectionConstraint(
                read_concern=ReadConcern(level='majority'),
                capped=True,
                max=100
            )
        ]
```


