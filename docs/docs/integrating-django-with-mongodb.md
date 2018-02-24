---
title: Integrating Django with MongoDB
permalink: /integrating-django-with-mongodb/
---

## A quick sanity test

While migrating Django to MongoDB for the **very first** time it is **highly recommended** to start on a new DB namespace, e.g. `myapp-djongo-db`. Use this empty DB in your `settings.py` file. 

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
3.  Open Django Admin, you should find all Models defined in your app, showing up in Django Admin (with no data!).

You can continue to work with this newly created DB by inserting data into the models from the Admin Interface. Continue reading further if you want to use Djongo with an existing MongoDB database.

## Using Djongo with an existing MongoDB database

As there is no concept of a AUTOINCREMENT field in MongoDB, internally Djongo creates a `__schema__` collection that tracks all auto increment fields in different tables. The `__schema__` collection has the form:

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
Every collection in the DB that has an autoincrement field has an entry in the `__schema__` collection. Running `manage.py migrate` automatically creates these entries. There are 3 ways to use Djongo with an existing DB

### Zero risk

1. Start with an empty db
2. In `models.py` define your models in Django, exactly the same as the fields in existing db.
3. Run `manage.py makemigarations <app_name>` followed by `manage.py migrate`. At the end of this step your empty db should have a `__schema__` collection as well as other collections defined in your model.py
4. Copy all data from existing db to new db
5. In `__schema__` collection make sure the `auto` field with `field_name` : `id`, `seq` number is incremented to the latest value corresponding to the copied data set. (`seq` will be 0 for all copied collections)

In case your seq number is not the latest value you run the risk of **overwriting** an existing entry with the new entry. But since you have a backup copy you are ok.

### Medium risk

If you don't want to create a new DB then follow step 1 to 3 as above followed by step 5. In step 4:

4. Copy the `__schema__` collection from the new DB to the existing DB

If you get step 5 wrong you may lose some data. You can delete the DB created in step 1.

### High risk

You can manually create the `__schema__` collection in your existing DB and add entries for each of the models your app uses in the format described above. This is quite tiresome and prone to manual errors.

*Now that you are done setting up Django with MongoDB, start using Django like you would with any other Database backend.*

## Database configuration

The following options are supported in `settings.py`:

```python
    DATABASES = {
        'default': {
            'ENGINE': 'djongo',
            'NAME': 'your-db-name',
            'HOST': 'host-name or ip address',
            'PORT': port_number,
            'USER': 'db-username',
            'PASSWORD': 'password',
            'AUTH_SOURCE': 'db-name',
            'AUTH_MECHANISM': 'SCRAM-SHA-1',
            'ENFORCE_SCHEMA': True
        }
    }
```

All options except `ENGINE` and `ENFORCE_SCHEMA` are the same those listed in the [pymongo documentation](http://api.mongodb.com/python/current/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient).

### Enforce schema

MongoDB is *schemaless*, which means that no schema is enforced by the database — we may add and remove fields however we want and MongoDB won’t complain. This makes life a lot easier in many regards, especially when there is a change to the data model. Take for example the `Blog` Model

```python
class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()
```

You can save several entries to this Model into the DB and then edit your Model sometime later like so:

```python
class Blog(models.Model):
    name = models.CharField(max_length=100)
    tagline = models.TextField()
    description = models.TextField()
```

You have just added a new field. The new entries can be saved into MongoDB **without running any migrations**. All entries in the Blog collection henceforth will contain 3 fields. This works fine if you know what you are doing. Consider a query that  retrieves entries belonging to both the 'older' model (with just 2 fields) and the current model. What will the value of `description` be? 

While connecting to Djongo you can set `ENFORCE_SCHEMA: True`. For the case described above, when field values are missing from the retrieved documents, Djongo will raise a `MigrationError` exception. You can then check what went wrong. Enforce schemas for our documents can help to iron out bugs involving incorrect types or missing fields.

`ENFORCE_SCHEMA: False` works by silently setting the missing fields with the value `None`. If your app is programmed to expect this (which means it's not a bug) you can get away by not calling any migrations.