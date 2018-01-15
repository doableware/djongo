# Integrating Django with MongoDB

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
    "_id" : ObjectId("59a25278a1b5e33724f9d9f0"), 
    "name" : "django_migrations", 
    "auto" : {
        "field_name" : "id", 
        "seq" : NumberInt(14)
    }
}
```
Every collection in the DB that has a autoincrement field has an entry in the schema collection. Running `manage.py migrate` automatically creates these entries. There are 3 ways to use Djongo with an existing DB

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

## Django ORM internals

The Django ORM can be broadly thought of as multiple Abstraction Layers stacked on top of each other.

<div style="max-width: 150px; margin-left: auto; margin-right: auto">
    <img src="/djongo/images/layers.svg" alt="Abstraction Layers">
</div>


### Models Layer

Your Django App and [Contrib](https://docs.djangoproject.com/en/dev/ref/contrib/) packages interface with the Models API to implement their functionality.

### Query Layer

The Query Layer converts Models functionality into Django SQL query strings that are similar to Sqllite query syntax. 

### DB connector

The Django SQL query string is converted to backend database specific SQL syntax. 

### Database

The Database only accepts SQL query string specific to its type.


## Ways to integrate Django with MongoDB

### From ORM to ODM

Object Document Mapping (ODM) is the Object Relational Mapping (ORM) for non-relational document oriented databases (like MongoDB). In an ODM, python objects (or group of them) are stored as documents instead of tables. Implementing an ODM for Django would entail rewriting several Django modules.

<div style="max-width: 400px; margin-left: auto; margin-right: auto">
    <img src="/djongo/images/orm2odm.svg" alt="Abstraction Layers">
</div>

#### Django-nonrel

[Django-nonrel](https://github.com/django-nonrel/django) aims to integrate Django and MongoDB but is not up to date with the latest version of Django.

#### django-mongo-engine

[MongoEngine](https://github.com/MongoEngine/mongoengine) is a Python Object-Document Mapper for working with MongoDB. [Django support in MongoEngine](https://mongoengine-odm.readthedocs.io/django.html) is split from the main MongoEngine repository for working with Django. 

### Django SQL to MongoDB transpiler

A different approach is to translate Django SQL query syntax into pymongo commands.

 <div style="max-width: 400px; margin-left: auto; margin-right: auto">
    <img src="/djongo/images/sql2mongodb.svg" alt="Abstraction Layers">
</div>

This has several advantages

#### Reuse Django Models
 
 Django is a stable framework with continuous development and enhancements. The [Django ORM](https://docs.djangoproject.com/en/dev/topics/db/models/) is quite extensive and feature rich. Defining *a third party* ORM to work with MongoDB means reproducing the entire Django ORM again. The new ORM needs to constantly align with the Django ORM. Several Django features will never make it into the third party ORM. The idea behind Djongo is to **reuse** existing Django ORM features by finally translating SQL queries to MongoDB syntax. 
 
#### Future proof your code
 
 As **SQL syntax will never change** regardless of future additions to Django, by using Djongo your code is now future proof!  
  
#### Stop the immigrations
 
MongoDB is a [schema free](https://docs.mongodb.com/manual/data-modeling/) DB. You no longer need to run <code> manage.py migrate</code> every time you change a model. Making changes to your models is easier.
  
#### Work on the Real Django

Djongo does not make you use a forked version of Django, access MongoDB with the Real Django framework. 

### Common misconceptions 

#### Relational data cannot be represented within a non relational data store

Relations between objects and subsequent joins can be done in non relational data stores by performing multiple [application level lookups](https://www.mongodb.com/blog/post/6-rules-of-thumb-for-mongodb-schema-design-part-2) 

#### Unstructured database cannot store structured data 
 
Unstructured data is a super set of structured data. Specifying the data structure to MongoDB will only be ignored by it.  

More details on [implementing Django MongoDB connector](/djongo/django-mongodb-connector-design-document/) can be found in the design document.
   
<script>
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-75159067-1', 'auto');
  ga('send', 'pageview');

</script>

