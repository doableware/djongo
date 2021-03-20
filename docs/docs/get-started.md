---
title: Get Started
permalink: /get-started/
description: "Djongo overcomes common pitfalls of PyMongo programming. It maps python objects to MongoDB documents. Setting up the mapping documents to python objects is easy with Djongo."
---

{{ page.notice.support }}

## Install
1. `pip install djongo`
2. Into `settings.py` file of your project, add:

      ```python
      DATABASES = {
          'default': {
              'ENGINE': 'djongo',
              'NAME': 'your-db-name',
          }
      }
      ```

3. YOU ARE SET! Have fun!

## Requirements
1. Python 3.6 or higher.
2. MongoDB 3.4 or higher.
3. If your models use nested queries or sub querysets like:
  
      ```python
      inner_query = Blog.objects.filter(name__contains='Ch').values('name')
      entries = Entry.objects.filter(blog__name__in=inner_query)
      ```
   MongoDB 3.6 or higher is required.

## Using MongoDB Fields

### EmbeddedField
 Nest a `dict` inside a model with the `EmbeddedField`. The `model_container` is used to describe the structure of the 
 data being stored.

```python
from djongo import models

class Blog(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        abstract = True

class Entry(models.Model):
    blog = models.EmbeddedField(
        model_container=Blog
    )    
    headline = models.CharField(max_length=255)    

e = Entry()
e.blog = {
    'name': 'Djongo'
}
e.headline = 'The Django MongoDB connector'
e.save()
```

### ArrayField
Nest a `list` of `dict` inside a model for more complex data.

```python
from djongo import models

class Entry(models.Model):
    blog = models.ArrayField(
        model_container=Blog
    )    
    headline = models.CharField(max_length=255)    

e = Entry()
e.blog = [
    {'name': 'Djongo'}, {'name': 'Django'}, {'name': 'MongoDB'}
]
e.headline = 'Djongo is the best Django and MongoDB connector'
e.save()
```
<!--
### JSONField


## Simplify complex queries

## Django Admin

-->

## Security and Integrity Checks
Djongo allows for checks on data fields before they are saved to the database. Running the correct integrity checks and field value validators before writing data into the database is important. 


### Validators
Apply validators to each field before they are saved.

```python
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from djongo import models
from django.core.validators import URLValidator

def script_injection(value):
    if value.find('<script>') != -1:
        raise ValidationError(_('Script injection in %(value)s'),
                              params={'value': value})

class Address(models.Model)
    city = models.CharField(max_length=50)
    homepage = models.URLField(validators=[URLValidator, script_injection])
    class Meta:
        abstract=True

class Entry(models.Model):
    _id = models.ObjectIdField()
    address = models.EmbeddedField(model_container=Address)
```

### Integrity checks

```python
class Entry(models.Model):
    _id = models.ObjectIdField()
    address = models.EmbeddedField(model_container=Address,
                                   null=False,
                                   blank=False)
```

By setting `null=False, blank=False` in `EmbeddedField`, missing values are never stored.

<!--
## Structured Data vs Flexibility
-->

## Database configuration

The `settings.py` supports (but is not limited to) the following  options:

Attribute | Value | Description
---------|------|-------------
ENGINE | djongo | The MongoDB connection engine for interfacing with Django.
ENFORCE_SCHEMA | True | Ensures that the model schema and database schema are exactly the same. Raises `Migration Error` in case of discrepancy.
ENFORCE_SCHEMA | False | (Default) Implicitly creates collections. Returns missing fields as `None` instead of raising an exception.
NAME | your-db-name | Specify your database name. This field cannot be left empty.
LOGGING | dict | A [dictConfig](https://docs.python.org/3.6/library/logging.config.html) for the type of logging to run on djongo.
CLIENT | dict | A set of key-value pairs that will be passed directly to [`MongoClient`](http://api.mongodb.com/python/current/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient) as kwargs while creating a new client connection.
  
All options except `ENGINE` and `ENFORCE_SCHEMA` are the same those listed in the [pymongo documentation](http://api.mongodb.com/python/current/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient).


```python
    DATABASES = {
        'default': {
            'ENGINE': 'djongo',
            'NAME': 'your-db-name',
            'ENFORCE_SCHEMA': False,
            'CLIENT': {
                'host': 'host-name or ip address',
                'port': port_number,
                'username': 'db-username',
                'password': 'password',
                'authSource': 'db-name',
                'authMechanism': 'SCRAM-SHA-1'
            },
            'LOGGING': {
                'version': 1,
                'loggers': {
                    'djongo': {
                        'level': 'DEBUG',
                        'propagate': False,                        
                    }
                },
             },
        }
    }
```

### Enforce schema

MongoDB is *schemaless*, which means no schema rules are enforced by the database. You can add and exclude fields per entry and MongoDB will not complain. This can make life easier, especially when there are frequent changes to the data model. Take for example the `Blog` Model (version 1).

```python
class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()
```

You can save several entries into the DB and later modify it to version 2:

```python
class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()
    description = models.TextField()
```

The modified Model can be saved **without running any migrations**. 

This works fine if you know what you are doing. Consider a query that retrieves entries belonging to both the 'older' model (with just 2 fields) and the current model. What will the value of `description` now be? To handle such scenarios Djongo comes with the `ENFORCE_SCHEMA` option. 

When connecting to Djongo you can set `ENFORCE_SCHEMA: True`. In this case, a `MigrationError` will be raised when field values are missing from the retrieved documents. You can then check what went wrong. 

`ENFORCE_SCHEMA: False` works by silently setting the missing fields with the value `None`. If your app is programmed to expect this (which means it is not a bug) you can get away by not calling any migrations.

## Djongo Manager

Djongo Manager extends the  functionality of the usual [Django Manager](https://docs.djangoproject.com/en/dev/topics/db/managers/). It gives direct access to the pymongo collection API. To use this manager define your manager as `DjongoManager` in the model.

 ```python
class Entry(models.Model):
    blog = models.EmbeddedField(
        model_container=Blog,
    )
    headline = models.CharField(max_length=255)    
    objects = models.DjongoManager()
```

Use it like the usual Django manager:

```python
post = Entry.objects.get(pk=p_key)
```

Will [get a model object](https://docs.djangoproject.com/en/dev/topics/db/queries/#retrieving-a-single-object-with-get) having primary key `p_key`.

### Using Pymongo commands 

MongoDB has powerful query syntax and `DjongoManager` lets you exploit it fully. For the above `Entry` model define a custom query function:

```python
class EntryView(DetailView):

    def get_object(self, queryset=None):
        index = [i for i in Entry.objects.mongo_aggregate([
            {
                '$match': {
                    'headline': self.kwargs['path']
                }
            },
        ])]

        return index

```

You can directly **access any** [pymongo command](https://api.mongodb.com/python/current/) by prefixing `mongo_` to the command name. 
{: .notice}

For example, to perform `aggregate` on the BlogPage collection (BlogPage is stored as a table in SQL or a collection in MongoDB) the function name becomes `mongo_aggregate`. To directly insert a document (instead of `.save()` a model) use `mongo_insert_one()`

## GridFS 

To save files using [GridFS](https://docs.mongodb.com/manual/core/gridfs/) you must create a file storage instance of `GridFSStorage`:

```python
grid_fs_storage = GridFSStorage(collection='myfiles')
```

In your model define your field as `FileField` or `ImageField` as usual:

```python
avatar = models.ImageField(storage=grid_fs_storage, upload_to='')
```

Refer to [Using GridFSStorage](/using-django-with-mongodb-gridfs/) for more details.

## DjongoNxt

Features under development at DjongoNxt are not a part of the standard Djongo package. Visit the [support page][support_page] for more information.
{: .notice--info}

DjongoNxt brings support to all features of MongoDB features including:

### Indexes

Support for indexes provided by MongoDB, for example 2dSphere Index, Text Index and Compound Indexes.

### Model Query

Support for GeoSpatial Queries and Tailable Cursors.

### Model Update

Unordered and Ordered Bulk Writes.

### Database Transactions

Atomic multi document transactions with commit and rollback support.

### Schema Validation and Model Creation

Automatic JSON Schema validation document generation and options to add Read and Write Concerns for the Models.

### Aggregation Operators 

Support for various aggregation operators provided by MongoDB.

## Contribute
 
If you think djongo is useful, **please share it** with the world! Your endorsements and online reviews will help get more support for this project.
  
You can contribute to the source code or the documentation by creating a simple pull request! You may want to refer to the design documentation to get an idea on how [Django MongoDB connector](/django-mongodb-connector-design-document/) is implemented.

{% include links %}
