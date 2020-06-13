---
title: Integrating Django with MongoDB
permalink: /integrating-django-with-mongodb/
description: "Djongo is a python connector for using the Django ORM with MongoDB. Use MongoDB as a backend database for your Django project, without changing the Django ORM. Start using Django with MongoDB by adding just one line of code"
---

Use MongoDB as a backend database for your Django project, without changing the Django ORM. Use Django Admin to add and modify documents in MongoDB. Start using Django with MongoDB by adding just one line of code. 

## Usage
1. pip install djongo
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
      inner_qs = Blog.objects.filter(name__contains='Ch').values('name')
      entries = Entry.objects.filter(blog__name__in=inner_qs)
      ```
   MongoDB 3.6 or higher is required.

## Support
[![Djongo Support](/djongo/assets/images/support.png)](https://www.patreon.com/nesdis/)

I am inundated daily with your appreciation, queries and feature requests for Djongo. Djongo has grown into a highly complex project. To support the requests, I have decided to follow an organized approach.

Djongo as a project is at a stage where its development must be transformed into a sustained effort. Djongo has more than [1,000,000 downloads](https://pypistats.org/packages/djongo) on pypi and continues to grow. I am trying to establish a sustainable development model for the project, and would [love to hear your thoughts.](https://www.patreon.com/posts/to-only-take-22611438)

Visit my [Patreon page](https://www.patreon.com/nesdis/) to make requests and for support. You can expect immediate answers to your questions.  

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
 
Get [expert support](https://www.patreon.com/nesdis) for complex projects.

## Rapid Prototyping
Djongo lets you rapidly develop and evolve your app models. Modifying your models is **much faster** with Djongo compared to traditional Django ORM. Since MongoDB is a schema-less database, every time you redefine a model, MongoDB does not expect you to redefine the schema. 

### Goodbye Migrations
With Djongo you **permanently  say goodbye** to Django Migrations. To enable migration free model evolution simply set `ENFORCE_SCHEMA: False` in your database configuration. Djongo no longer interprets SQL DDL statements (example CREATE TABLE) to emit pymongo `create_collection` commands. With `ENFORCE_SCHEMA: False` collections are created implicitly, on the fly.

## Data security and integrity checks
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
## Using MongoDB fields

## Simplify complex queries

## Django Admin

-->

## DjongoNxt

> Features supported in DjongoNxt are not a part of the standard Djongo package. Visit the [sponsors page](https://www.patreon.com/nesdis/) for more information.

DjongoNxt is a Django and MongoDB connector for full featured database usage. It provides many features of MongoDB enabled through Django. It comes with support for:

### Indexes

Support for all indexes provided by MongoDB, for example 2dSphere Index, Text Index and Compound Indexes.

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
  
You can contribute to the source code or the documentation by creating a simple pull request! You may want to refer to the design documentation to get an idea on how [Django MongoDB connector](/djongo/django-mongodb-connector-design-document/) is implemented.
 
Please contribute to the continued development and success of Djongo by [making a donation](https://www.patreon.com/nesdis/).