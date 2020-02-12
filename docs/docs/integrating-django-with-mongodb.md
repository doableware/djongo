---
title: Integrating Django with MongoDB
permalink: /integrating-django-with-mongodb/
---

## A quick sanity test

When migrating Django to MongoDB for the **very first** time, it is **recommended** to start on a new DB namespace. For example, use `myapp-djongo-db` in your `settings.py` file. 

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
3.  Open Django Admin and you should find all Models defined in your app, showing up in Django Admin (with no data!).

You can continue to work with this new DB. Start by inserting data into the models from the Admin interface. 

You may want to go through the quick [get started](/djongo/get-started) guide for setting up Djongo before proceeding ahead. An introduction to [using MongoDB fields in Django](/djongo/using-django-with-mongodb-data-fields/) can prove useful.

## Database configuration

The `settings.py` supports (but is not limited to) the following  options:

```python
    DATABASES = {
        'default': {
            'ENGINE': 'djongo',
            'ENFORCE_SCHEMA': True,
            'LOGGING': {
                'loggers': {
                    'djongo': {
                        'level': 'DEBUG',
                        'propogate': False,
                        'handlers': ['console']
                    }
                },
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'level': 'DEBUG'
                    }
                }
            },
            'NAME': 'your-db-name',
            'CLIENT': {
                'host': 'host-name or ip address',
                'port': port_number,
                'username': 'db-username',
                'password': 'password',
                'authSource': 'db-name',
                'authMechanism': 'SCRAM-SHA-1'
            }
        }
    }
```

All options except `ENGINE` and `ENFORCE_SCHEMA` are the same those listed in the [pymongo documentation](http://api.mongodb.com/python/current/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient).

Attribute | Value | Description
---------|------|-------------
ENGINE | djongo | The MongoDB connection engine for interfacing with Django.
ENFORCE_SCHEMA | True | (Default) Ensures that the model schema and database schema are exactly the same. Raises `Migration Error` in case of discrepancy. 
ENFORCE_SCHEMA | False | Implicitly creates collections. Returns missing fields as `None` instead of raising an exception.
NAME | your-db-name | Specify your database name. This field cannot be left empty.
LOGGING | dict | A [dictConfig](https://docs.python.org/3.6/library/logging.config.html) for the type of logging to run on djongo.
CLIENT | dict | A set of key-value pairs that will be passed directly to [`MongoClient`]((http://api.mongodb.com/python/current/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient)) as kwargs while creating a new client connection.
  

### Enforce schema

MongoDB is *schemaless*, which means that no schema is enforced by the database — you can add and remove fields the way you want and MongoDB will not complain. This makes life a lot easier in many regards, especially when there are frequent changes to the data model. Take for example the `Blog` Model.

```python
class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()
```

You can save several entries into the DB and later modify it like so:

```python
class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()
    description = models.TextField()
```

The modified Model can be saved **without running any migrations**. All entries in the `Blog` collection will now contain 3 fields. 

This works fine if you know what you are doing. Consider a query that retrieves entries belonging to both the 'older' model (with just 2 fields) and the current model. What will the value of `description` now be? 

To handle such scenarios Djongo comes with the `ENFORCE_SCHEMA` option. When connecting to Djongo you can set `ENFORCE_SCHEMA: True`. In this case, a `MigrationError` will be raised when field values are missing from the retrieved documents. You can then check what went wrong. Enforce schema can help to iron out bugs involving incorrect types or missing fields.

`ENFORCE_SCHEMA: False` works by silently setting the missing fields with the value `None`. If your app is programmed to expect this (which means it is not a bug) you can get away by not calling any migrations.

## Use Django Admin to add documents

Let’s say you want to create a blogging platform using Django with MongoDB as your backend.
In your Blog `app/models.py` file define the `Blog` model:

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


![Django Admin](/djongo/assets/images/admin.png)


### Querying Embedded fields

In the above example, to query all Entries with Blogs which have names that start with *Beatles*, use the following query:

```python
entries = Entry.objects.filter(blog__startswith={'name': 'Beatles'})
```

Refer to [Using Django with MongoDB data fields](/djongo/using-django-with-mongodb-data-fields/) for more details.

## Djongo Manager

Djongo Manager extends the  functionality of the usual [Django Manager](https://docs.djangoproject.com/en/dev/topics/db/managers/). It gives access to  the complete pymongo collection API. Define your manager as Djongo Manager in the model.

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

### Tunnel directly to Pymongo 

MongoDB has powerful query syntax and `DjongoManager` lets you exploit it fully.

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

You can directly *access any [pymongo](https://api.mongodb.com/python/current/) command* by prefixing `mongo_` to the command name. For example, to perform `aggregate` on the BlogPage collection (BlogPage is stored as a table in SQL or a collection in MongoDB) the function name becomes `mongo_aggregate`. To directly insert a document (instead of `.save()` a model) use `mongo_insert_one()`

## GridFS 

To save files using [GridFS](https://docs.mongodb.com/manual/core/gridfs/) you must create a file storage instance of `GridFSStorage`:

```python
grid_fs_storage = GridFSStorage(collection='myfiles')
```

In your model define your field as FileField or ImageField as usual:

```python
avatar = models.ImageField(storage=grid_fs_storage, upload_to='')
```

Refer to [Using GridFSStorage](/djongo/using-django-with-mongodb-gridfs/) for more details.

## Migrating your data

There is no concept of an AUTOINCREMENT field in MongoDB. Internally, Djongo creates a `__schema__` collection. This collection is used to track all auto increment fields in different tables. The `__schema__` collection looks like:

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
For every collection in the DB that has an autoincrement field, there is an corresponding entry in the `__schema__` collection. Running `manage.py migrate` automatically creates these entries. There are 3 approaches to use Djongo with an existing DB.

### Zero risk

1. Start with an empty DB.
2. Define your models in the `models.py` file, if you have not already done so. The models and model fields have to be exactly the same, as the fields in the existing DB.
3. Run `manage.py makemigrations <app_name>` followed by `manage.py migrate`. At the end of this step your empty DB should have a `__schema__` collection, and other collections defined in the `model.py` file.
4. Copy all data from the existing DB to the new DB.
5. In `__schema__` collection make sure that the `seq` number is incremented to the latest value. This should correspond to the document count for each model. For example, if your model has 16 entries (16 documents in the DB), then `seq` should be set as 16.

In case your seq number is not the latest value you run the risk of **overwriting** an existing entry with the new entry. But since you have a backup, you are okay.

### Medium risk

If you do not want to create a new DB.

1. Start with an empty DB. You can always delete this later.
2. Same as before.
3. Same as before.
4. Copy the `__schema__` collection from the new DB to the existing DB.
5. Same as before.

You can now delete the DB created in step 1.

### High risk

You can manually create a `__schema__` collection in your existing DB. Next, add entries for each model your app uses in the format described above. This can be quite tiresome, and prone to manual errors.

*You are now done setting up Django with MongoDB. Start using Django with MongoDB, like you would with any other database backend.*

Finally, you can ask for [expert support](https://www.patreon.com/nesdis) if your project demands complex migrations.


