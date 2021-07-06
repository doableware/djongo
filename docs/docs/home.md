---
permalink: /
layout: splash
title: "Unified Database Query"
excerpt: 
tagline: Deploy a Multi-DB Enabled Backend Server Instantly

description: "Djongo is a smarter approach to database querying. It maps python objects to MongoDB documents. It can be used with both relational and non-relational databases."

classes:
    - feature-page
    - l-splash-full

header:
    overlay_image: /assets/images/home/banner-rand-dark-many6.png
    overlay_color_dark: #092e20
    overlay_color: #09411f
    cta_url: /support/
    cta_label: "Deploy"       

---


{% comment %}
query
Easily create and query [embedded documents](/using-django-with-mongodb-data-fields/) 
     and [arrays](/using-django-with-mongodb-array-field/). Add
    MongoDB specific [indexes](/djongonxt-indexes/), [transactions](djongonxt-database-transactions/),
    and much more."

    skip migrations, and [autogenerate complex queries](/djongo/using-django-with-mongodb-array-reference-field/)."  

{% endcomment %}

{% capture content %}

## Djongo
![Djongo](/assets/images/home/djongo-name-logo.png){: .img-right .sz-sm .top-align}
Djongo is a smarter approach to database querying. It is an extension to the traditional [Django ORM](https://www.djangoproject.com/) framework. It maps python objects to MongoDB documents, a technique popularly referred to as Object Document Mapping or ODM.

Constructing queries using Djongo is **much easier** compared to writing lengthy Pymongo query documents.
Storing raw `JSON` emitted by the frontend directly into the database is scary. Djongo ensures that **only clean data** gets through. 

**You no longer** need to use the shell to inspect your data. By using the `Admin` package, you can access and modify data directly from the web browser.
 Djongo includes handy UI elements that help represent MongoDB documents on the browser. 

::
## Security and Integrity Checks

```python
def script_injection(value):
  if value.find('<script>') != -1:
    raise ValidationError(_('Script injection in %(value)s'),
                            params={'value': value})

class Entry(models.Model):
  homepage = models.URLField(validators=[URLValidator,
                                         script_injection])
```
{: .code-left .top-align}

Djongo performs **checks on data fields** before they are saved to the database. 

Define **custom validators** or use builtin validators to check the data. Validation is triggered prior to writing to the database.

Running **integrity checks** and field value validators ensures protect from garbage data. 

::
## Rapid Prototyping

![Djongo](/assets/images/home/rapid-levels.png){: .img-right .sz-sm }
As your data evolves you may wish to enforce a structure to it. The `JSONField` represents documents with no structure, and **no validations**. 

The `EmbeddedField` lets you describe the structure which triggers automatic **validations at the application level**.

Setting `enforce_schema = True` in the `settings.py` file enables schema **checks at the database level**.

::
## Query Creation

{% capture pymongo %}
```python
self.db['entry'].aggregate(
    [{
        '$match': {
          'author_id': {
            '$ne': None,
            '$exists': True
          }
        }
      },
      {
        '$lookup': {
          'from': 'author',
          'localField': 'author_id',
          'foreignField': 'id',
          'as': 'author'
        }
      },
      {
        '$unwind': '$author'
      },
      {
        '$lookup': {
          'from': 'blog',
          'localField': 'blog_id',
          'foreignField': 'id',
          'as': 'blog'
        }
      },
      {
        '$unwind': {
          'path': '$blog',
          'preserveNullAndEmptyArrays': True
        }
      },
      {
        '$addFields': {
          'blog': {
            '$ifNull': ['$blog', {
              'id': None,
              'title': None
            }]
          }
        }
      },
      {
        '$match': {
          'author.name': {
            '$eq': 'Paul'
          }
        }
      }, 
      {
        '$project': {
          'id': True,
          'blog_id': True,
          'author_id': True,
          'content': True,
          'blog.id': True,
          'blog.title': True
        }
      }]
```
{: .sz-short}
{% endcapture %}

{% capture djongo %}
```python
qs = Entry.objects.filter(author__name='Paul')\
                  .select_related('blog')
```
{: .sz-short}
{% endcapture %}

{% include feature_page/home/query.html pymongo=pymongo djongo=djongo %}

Djongo generates complex, error free, aggregation queries automatically.
It takes the relatively simple query on the right 
and **automatically generates** the pymongo query document on the left.

::
## Installation and Setup

Download and install the latest version of Djongo by running:

```
pip install djongo
```

The project directory is where all Djongo settings live. Auto generate the required files by running:

```
django-admin startproject mysite
```

You can replace *mysite* with a name of your choosing.
Go into the root of *mysite* directory to find the `settings.py` file. Add:

```python
  DATABASES = {
      'default': {
          'ENGINE': 'djongo',
          'NAME': 'your-db-name',
      }
  }
```

YOU ARE SET! Have fun!

[Get Started](/get-started){: .btn .btn--primary .btn--large}
{: .text-center}

{% endcapture %}

{% include feature_page/features.html 
    content=content
    card=site.data.home %}
