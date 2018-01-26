---
title: Integrating Django with MongoDB
permalink: /integrating-django-with-mongodb/
---


This document is a tutorial on how to integrate MongoDB with Django with focus on Djongo. It describes the Django ORM internal implementation that is not covered by the [Django documentation](https://docs.djangoproject.com/en/dev/). If you have not yet checked out the [introduction to Djongo](https://nesdis.github.io/djongo/), be sure to do so! 

There are different ways to integrate MongoDB with Django, each with positives and negatives. Insights into the Django ORM design will help understand ways to integrate MongoDB and Django.     

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
        }
    }
```
## Using Djongo with an existing MongoDB database

As there is no concept of AUTOINCREMENT fields in MongoDB, internally Djongo creates a `__schema__` collection that tracks all auto increment fields in different tables. The `__schema__` collection has the form:

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
Every collection in the DB that has an autoincrement field has an entry in the schema collection. Running `manage.py migrate` automatically creates these entries. There are 3 ways to use Djongo with an existing DB

### Zero risk

1. Start with an empty db
2. In `models.py ` define your models in Django exactly the same as the fields in existing db.
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

