---
title: Django and MongoDB connector
permalink: "/get-started/"
---


Use MongoDB as a backend database for your Django project, without changing the Django ORM. Use the Django Admin app to add and modify documents in MongoDB. 

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
  
3. Run `manage.py makemigrations <app_name>` followed by `manage.py migrate` (ONLY the first time to create collections in MongoDB)
4. YOU ARE SET! Have fun!

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

I am inundated daily with your appreciation, queries and feature requests for Djongo. Djongo has grown into more than a simple hobby project of an individual developer. To support the requests, I have decided to follow an organized approach.

Djongo as a project is at a stage where its development must be transformed into a sustained effort. Djongo has more than [100,000 downloads](https://pypistats.org/packages/djongo) on pypi and continues to grow. I am trying to establish a sustainable development model for the project, and would [love to hear your thoughts.](https://www.patreon.com/posts/to-only-take-22611438)

Visit my [Patreon page](https://www.patreon.com/nesdis/) to make requests and for support.

## How it works

Djongo makes minimal changes to the existing Django ORM framework, which means unnecessary bugs do not crop up. It simply translates a SQL query string into a [MongoDB query document](https://docs.mongodb.com/manual/tutorial/query-documents/). As a result, all Django features, models, etc., work as is.
  
Django contrib modules: 

```python
'django.contrib.admin',
'django.contrib.auth',    
'django.contrib.sessions',
```
and others... fully supported.
  
## What you get

Djongo ensures that you:

 * Reuse Django Models/ORM
 * Work with the original Django variant
 * Future proof your code
 * Atomic SQL JOIN operations
 
Get [expert support](https://www.patreon.com/nesdis) for complex projects.


## Contribute
 
If you think djongo is useful, **please share it** with the world! Your endorsements and online reviews will help get more support for this project.
  
You can contribute to the source code or the documentation by creating a simple pull request! You may want to refer to the design documentation to get an idea on how [Django MongoDB connector](/djongo/django-mongodb-connector-design-document/) is implemented.
 
Please contribute to the continued development and success of Djongo by [making a donation](https://www.patreon.com/nesdis).

