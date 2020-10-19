---
permalink: /
layout: splash
title: "MongoDB Document Mapper"
excerpt: 

description: "Djongo is a smarter approach to pymongo programming. It maps python objects to MongoDB documents. It is popularly referred to as an Object Document Mapper or ODM. It is an extension to the traditional Django object relational modeling framework. Use Django Admin to directly add and modify documents stored in MongoDB. Use other contrib modules such as Auth and Sessions without any changes."

classes:
    - landing-page
    
header:
    overlay_image: /assets/images/landing/landing-banner-narrow-2.png
    overlay_color: #092e20

        
punchline:
  - excerpt: Python Object to MongoDB Document Mapping Framework

value_row_first:
  - image_path: /assets/images/landing/security-green.png
    alt: "Security"
    title: "Security"
    excerpt: "Directly saving raw `JSON` into the database is scary. Djongo secures and validates the `JSON` document before saving."
    
  - image_path: /assets/images/landing/query-green-own.png
    alt: "Simplify Query Creation"
    title: "Simplify Query Creation"
    excerpt: "Writing query documents can get out of control. Djongo does the heavy lifting of creating query documents for you." 

  - image_path: /assets/images/landing/webpage.png
    alt: "Web Interface"
    title: "Web Interface"
    excerpt: "Access and modify MongoDB through the web browser."

  - image_path: /assets/images/landing/support-new.png
    alt: "Support"
    title: "Support"
    excerpt: "Get support for queries on MongoDB document modeling."
    url: /support/
    btn_label: "Learn More"
    btn_class: "btn--primary"
    
  - image_path: /assets/images/landing/rapid.png
    alt: "Rapid Prototyping"
    title: "Rapid Prototyping"
    excerpt: "Speed up app development and execution with schema free models. Enforce different levels of 
              schema protection based on your data evolution." 
      
  - image_path: /assets/images/landing/third-party-thin.png
    alt: "Admin MongoDB"
    title: "Third Party Packages"
    excerpt: "Modules that help interface your MongoDB data with other popular packages."

djongonxt_row:
  - image_path: /assets/images/landing/djongo-Nxt-v1.png
    alt: "Djongo Next"
    title: "Djongo Next"
    excerpt: "The advanced modeling framework. Ships with extra features for professional usage."
    url: /support/
    btn_label: "Learn More"
    btn_class: "btn--primary"
  
    
advert_row:
  - image_path: /assets/images/landing/e2e.png
    alt: "Admin MongoDB"
    image_link: http://www.e2eprojects.com/
    
  - image_path: /assets/images/white.jpg
    alt: "Admin MongoDB"

  - image_path: /assets/images/landing/sumeru.png
    alt: "Admin MongoDB"
    image_link: https://www.sumerusolutions.com/

---

{% include feature_row id="punchline" type="center" %}

{% comment %}
{% include advert_row %}

query
Easily create and query [embedded documents](/djongo/using-django-with-mongodb-data-fields/) 
     and [arrays](/djongo/using-django-with-mongodb-array-field/). Add
    MongoDB specific [indexes](/djongo/djongonxt-indexes/), [transactions](djongonxt-database-transactions/),
    and much more."

    skip migrations, and [autogenerate complex queries](/djongo/using-django-with-mongodb-array-reference-field/)."  

{% endcomment %}

{% include feature_row id="value_row_first" %}


![Djongo](/djongo/assets/images/landing/djongo-symbol.png){: .align-right .djongo-symbol}
Djongo is an extension to the traditional Django ORM framework. It maps python objects to MongoDB documents, a technique popularly referred to as Object Document Mapping or ODM.

Constructing queries is much easier compared to manually writing lengthy query documents with pymongo. Djongo automatically creates complex query documents for you.
Storing raw `JSON` emitted by the frontend directly into the database is scary. Djongo ensures that only clean data gets through. 

You no longer need to use the shell to inspect your data. By using the `Admin` package, you can access and modify data directly from the web browser. Djongo carries handy UI elements that help represent MongoDB documents on the browser. 

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
{: .code-block--left }

Djongo performs checks on data fields before they are saved to the database. 
{: .text-left}

Define custom validators or use builtin validators to check the data. Validation is triggered prior to writing to the database.
{: .text-left}

Running integrity checks and field value validators ensures protect from garbage data. 
{: .text-left}

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
{: .query__code }
{% endcapture %}

{% capture djongo %}
```python
qs = Entry.objects.filter(author__name='Paul')\
                  .select_related('blog')
```
{: .query__code .code-small}
{% endcapture %}

{% include landing/query.html pymongo=pymongo djongo=djongo %}

Djongo generates complex, error free, aggregation queries automatically. It takes the relatively simple query on the left 
and generates the pymongo query document on the right.

## Rapid Prototyping

![Djongo](/djongo/assets/images/landing/rapid-levels.png){: .align-right .djongo-symbol}

As your data evolves you may wish to enforce a structure to it. Starting with the `JSONField` which represents documents with no structure, to setting `enforce_schema = True` in the `settings.py` file that enables checks  to the structure of the data being stored. 

Use the `JSONField` to store arbitrary documents into a collection. The `EmbeddedField` lets you describe a structure to the documents. Automatic validations at the application level are then performed to the document schema before being saved.

You can enable the automatic creation of  MongoDB schema documents inside a `model`. Schema checks to the documents being stored are then performed for that particular collection at the database level. Finally, setting `enforce_schema = True` in the `settings.py` file results in the checking of document schema for all the collections in the database.

[Get Started](/djongo/get-started){: .btn .btn--primary .btn--large}
{: .text-center}


{% comment %}
    {% include feature_row id="djongonxt_row" type="center" %}
{% endcomment %}

