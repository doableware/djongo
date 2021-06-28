---
title: Djongo vs Others
permalink: /djongo-comparison/
description: This page describes how to integrate MongoDB with Django with focus on Djongo. It describes the Django ORM internal implementation that is not covered by the Django documentation.
classes:
    - l-docs
---

This page describes how to integrate MongoDB with Django with focus on Djongo. It describes the Django ORM internal implementation that is not covered by the [Django documentation](https://docs.djangoproject.com/en/dev/). If you have not yet checked out the [introduction to Djongo](https://www.djongomapper.com/), be sure to do so first! 

There are different ways to integrate MongoDB with Django, each with positives and negatives. Insights into the Django ORM design will help understand ways to integrate MongoDB and Django. 

## Django ORM internals

The Django ORM can be broadly thought of as multiple Abstraction Layers stacked on top of each other.

<div style="max-width: 150px; margin-left: auto; margin-right: auto">
    <img src="/assets/images/layers.png" alt="Abstraction Layers">
</div>


## Models Layer

Your Django App and [Contrib](https://docs.djangoproject.com/en/dev/ref/contrib/) packages interface with the Models API to implement their functionality.

## Query Layer

The Query Layer converts Models functionality into Django SQL query strings that are similar to Sqllite query syntax. 

## DB connector

The Django SQL query string is converted to backend database specific SQL syntax. 

## Database

The Database only accepts SQL query string specific to its type.


## Ways to integrate Django with MongoDB

### From ORM to ODM

Object Document Mapping (ODM) is the Object Relational Mapping (ORM) for non-relational document oriented databases (like MongoDB). In an ODM, python objects (or group of them) are stored as documents instead of tables. Implementing an ODM for Django would entail rewriting several Django modules.

<div style="max-width: 400px; margin-left: auto; margin-right: auto">
    <img src="/assets/images/orm2odm.png" alt="Abstraction Layers">
</div>

### Django-nonrel

[Django-nonrel](https://github.com/django-nonrel/django) aims to integrate Django and MongoDB but is not up to date with the latest version of Django.

## Django SQL to MongoDB transpiler

A different approach is to translate Django SQL query syntax into pymongo commands.

 <div style="max-width: 400px; margin-left: auto; margin-right: auto">
    <img src="/assets/images/sql2mongodb.png" alt="Abstraction Layers">
</div>

This has several advantages

### Reuse Django Models
 
 Django is a stable framework with continuous development and enhancements. The [Django ORM](https://docs.djangoproject.com/en/dev/topics/db/models/) is quite extensive and feature rich. Defining *a third party* ORM to work with MongoDB means reproducing the entire Django ORM again. The new ORM needs to constantly align with the Django ORM. Several Django features will never make it into the third party ORM. The idea behind Djongo is to **reuse** existing Django ORM features by finally translating SQL queries to MongoDB syntax. 
 
### Future proof your code
 
 As **SQL syntax will never change** regardless of future additions to Django, by using Djongo your code is now future proof!  
  
### Goodbye migrations 
 
MongoDB is a [schema free](https://docs.mongodb.com/manual/data-modeling/) DB. You no longer need to run <code> manage.py migrate</code> every time you change a model. Making changes to your models is easier.
  
### Work on the Real Django

Djongo does not make you use a forked version of Django, access MongoDB with the Real Django framework. 

## Common misconceptions 

### Relational data cannot be represented within a non relational data store

Relations between objects and subsequent joins can be done in non relational data stores by performing multiple [application level lookups](https://www.mongodb.com/blog/post/6-rules-of-thumb-for-mongodb-schema-design-part-2) 

### Unstructured database cannot store structured data 
 
Unstructured data is a super set of structured data. Specifying the data structure to MongoDB will only be ignored by it.  

More details on [implementing Django MongoDB connector](/django-mongodb-connector-design-document/) can be found in the design document.
   

