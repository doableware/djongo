---
title: Django with MongoDB
permalink: /integrating-django-with-mongodb/
description: "Djongo is an extension to the Django ORM. Use MongoDB as the backend for your Django project, without changing the Django ORM.
Use Django Admin to directly add and modify documents stored in MongoDB. Use other contrib modules such as Auth
and Sessions without any changes. Start using Django with MongoDB by adding just one line of code"
layout: docs
---

Use MongoDB as a backend database for your Django project, without changing the Django ORM. Use Django Admin to add and modify documents in MongoDB. Start using Django with MongoDB by adding just one line of code. 


## How it works
Djongo makes **zero changes** to the existing Django ORM framework, which means unnecessary bugs and security vulnerabilities do not crop up. It simply translates a SQL query string into a [MongoDB query document](https://docs.mongodb.com/manual/tutorial/query-documents/). As a result, all Django features, models, etc., work as is.
  
Django contrib modules: 

```python
'django.contrib.admin',
'django.contrib.auth',    
'django.contrib.sessions',
```
and others... fully supported.
  
## What you get
Djongo ensures that you:

 * Reuse Django Models/ORM.
 * Work with the original Django variant.
 * Future proof your code.
 * Atomic SQL JOIN operations.
 
Get [expert support][support_page] for complex projects.

## Rapid Prototyping
Djongo lets you rapidly develop and evolve your app models. Modifying your models is **much faster** with Djongo compared to traditional Django ORM. Since MongoDB is a schema-less database, every time you redefine a model, MongoDB does not expect you to redefine the schema. 

### Goodbye Migrations
With Djongo you **permanently  say goodbye** to Django Migrations. To enable migration free model evolution simply set `ENFORCE_SCHEMA: False` in your database configuration. Djongo no longer interprets SQL DDL statements (example CREATE TABLE) to emit pymongo `create_collection` commands. With `ENFORCE_SCHEMA: False` collections are created implicitly, on the fly.

## Use Django Admin to add documents

The Django Admin interface can be used to work with MongoDB. Additionally, several MongoDB specific features are supported using [EmbeddedField](/using-django-with-mongodb-data-fields/), [ArrayField](/using-django-with-mongodb-array-field/) and other fields. Let’s say you want to create a blogging platform using Django with MongoDB as your backend. In your Blog `app/models.py` file define the `Blog` model:

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

Refer to [Using Django with MongoDB data fields](/using-django-with-mongodb-data-fields/) for more details.

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
4. While the relevant collections have been created in MongoDB, they have no data inside.
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
