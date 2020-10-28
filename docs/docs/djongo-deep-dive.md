---
title: Django and MongoDB connector
permalink: /djongo-deep-dive/
---

{{ page.notice.sponsor }}

## Database configuration

The `settings.py` supports (but is not limited to) the following  options:

Attribute | Value | Description
---------|------|-------------
ENGINE | djongo | The MongoDB connection engine for interfacing with Django.
ENFORCE_SCHEMA | True | Ensures that the model schema and database schema are exactly the same. Raises `Migration Error` in case of discrepancy.
ENFORCE_SCHEMA | False | (Default) Implicitly creates collections. Returns missing fields as `None` instead of raising an exception.
NAME | your-db-name | Specify your database name. This field cannot be left empty.
LOGGING | dict | A [dictConfig](https://docs.python.org/3.6/library/logging.config.html) for the type of logging to run on djongo.
CLIENT | dict | A set of key-value pairs that will be passed directly to [`MongoClient`]((http://api.mongodb.com/python/current/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient)) as kwargs while creating a new client connection.
  
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

## Use Django Admin to add documents

The Django Admin interface can be used to work with MongoDB. Additionally, several MongoDB specific features are supported using [EmbeddedField](/djongo/using-django-with-mongodb-data-fields/), [ArrayField](/djongo/using-django-with-mongodb-array-field/) and other fields. Let’s say you want to create a blogging platform using Django with MongoDB as your backend. In your Blog `app/models.py` file define the `Blog` model:

```python
from djongo import models

class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()

    class Meta:
        abstract = True
```

Now ‘embed’ your `Blog` inside a `Entry` using the `EmbeddedField`:

```python
class Entry(models.Model):
    blog = models.EmbeddedField(
        model_container=Blog,
    )
    
    headline = models.CharField(max_length=255)
```

Register your `Entry` in `admin.py`:

```python
from django.contrib import admin
from .models import Entry

admin.site.register(Entry)
```

That’s it you are set! Fire up Django Admin on localhost:8000/admin/ and this is what you get:


![Django Admin](/assets/images/admin.png)


### Querying Embedded fields

In the above example, to query all Entries with Blogs which have names that start with *Beatles*, use the following query:

```python
entries = Entry.objects.filter(blog__startswith={'name': 'Beatles'})
```

Refer to [Using Django with MongoDB data fields](/djongo/using-django-with-mongodb-data-fields/) for more details.

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

Refer to [Using GridFSStorage](/djongo/using-django-with-mongodb-gridfs/) for more details.


## Migrating an existing Django app to MongoDB

When migrating an existing Django app to MongoDB,  it is recommended to start a new database on MongoDB. For example, use `myapp-djongo-db` in your `settings.py` file. 

1. Into `settings.py` file of your project, add:

    ```python
      DATABASES = {
          'default': {
              'ENGINE': 'djongo',
              'NAME': 'myapp-djongo-db',
          }
      }
    ```
  
2. Run `manage.py makemigrations <myapp>` followed by `manage.py migrate`.
3. Open Django Admin and you should find all Models defined in your app, showing up in the Admin.
4. While the relevant collections have been created in MongoDB, they have have no data inside.
5. Continue by inserting data into the collections manually, or use Django Admin for a GUI. 

## Setting up an existing MongoDB database on Django

### The internal `__schema__` collection

There is no concept of an AUTOINCREMENT field in MongoDB. Therefore, Djongo internally creates a `__schema__` collection to track such fields. The `__schema__` collection looks like:

```python
{ 
    "_id" : ObjectId("5a5c3c87becdd9fe2fb255a9"), 
    "name" : "django_migrations", 
    "auto" : {
        "field_names" : [
            "id"
        ], 
        "seq" : NumberInt(14)
    }
}
```
For every collection in the DB that has an autoincrement field, there is a corresponding entry in the `__schema__` collection. Running `manage.py migrate` automatically creates these entries. 

Now there are 2 approaches to setting up your existing data onto MongoDB:

### Zero risk

1. Start with a new database name in `settings.py`.
2. If you have not already done so, define your models in the `models.py` file. The model names and model fields have to be exactly the same, as the existing data that you want to setup.
3. Run `manage.py makemigrations <app_name>` followed by `manage.py migrate`. 
4. Now your empty DB should have a `__schema__` collection, and other collections defined in the `model.py` file.
5. Copy collection data (of your custom models defined in `model.py`) to the new DB.
6. In `__schema__` collection make sure that the `seq` number of your AUTOINCREMENT fields is **set to the latest value**. This should correspond to the document count for each model. For example, if your model has 16 entries (16 documents in the DB), then `seq` should be set as 16. Usually the AUTOINCREMENT field is called `id`.

However, if you do not want to create a new database (and copy existing data into this new database), you can try this approach:

### Medium risk

1. Start with an empty database. You can always delete this later.
2. Same as before.
3. Same as before.
4. Now copy the `__schema__` collection from the new database (from step1) to the existing database.
5. Same as step 6 from before.
6. You can now delete the database created in step 1.

*You are now done setting up Django with MongoDB. Start using Django with MongoDB, like you would with any other database backend.*

{% include links %}