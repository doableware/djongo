<h1>djongo</h1>

[![Build Status](https://travis-ci.com/nesdis/djongo.svg?branch=master)](https://travis-ci.com/nesdis/djongo)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
<a href="https://badge.fury.io/py/djongo"><img src="https://badge.fury.io/py/djongo.svg" alt="PyPI version" height="18"></a>

 ## The only connector that let's you use Django with MongoDB *without* changing the Django ORM

Use MongoDB as a backend database for your Django project, without changing the Django ORM. Use the Django Admin GUI to add and modify documents in MongoDB. 

## Usage:
<ol>
<li> Install djongo:

``` 
pip install djongo
```
</li>
<li> Into settings.py file of your project, add: 

```python
DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': 'your-db-name',
        'HOST': 'your-db-host',
    }
}
```
</li>   
   <li> Run <code>manage.py makemigrations &ltapp_name&gt </code> followed by <code>manage.py migrate</code> (ONLY the first time to create collections in mongoDB) </li>
   <li> YOUR ARE SET! HAVE FUN! </li>
</ol>

## Requirements:

  1. Python 3.6 or higher.
  2. MongoDB 3.4 or higher.
  3. If your models use nested queries or sub querysets like:
  
      ```python
      inner_qs = Blog.objects.filter(name__contains='Ch').values('name')
      entries = Entry.objects.filter(blog__name__in=inner_qs)
      ```
     MongoDB 3.6 or higher is required.

## Dear Supporter

I am inundated daily with your love, appreciation, queries and feature requests for Djongo. Djongo has grown into more than a simple hobby project of an individual developer. Visit my [Patreon page](https://www.patreon.com/nesdis) to understand the different levels of support and services you can get.

## How it works

djongo is a SQL to mongodb query compiler. It translates a SQL query string into a mongoDB query document. As a result, all Django features, models etc work as is.
  
  Django contrib modules: 
<pre><code>  
'django.contrib.admin',
'django.contrib.auth',    
'django.contrib.sessions',

</code></pre>
 and others... fully supported.

## Features

  * Use Django Admin GUI to access MongoDB.  
  * Embedded Model.
  * Embedded Array.
  * Embedded Form Fields.
  
  Read the [full documentation](https://nesdis.github.io/djongo/)
  
## Contribute
 
 If you think djongo is useful, **please share it** with the world! Your endorsements and online reviews will help get more support for this project.
  
 Take a look at the [Enhancements project](https://github.com/nesdis/djongo/projects/1) that contains a list of features that must be implemented in future versions of Djongo. You can contribute to the source code or the documentation by creating a simple pull request! You may want to refer to the design documentation to get an idea on how [Django MongoDB connector](https://nesdis.github.io/djongo/django-mongodb-connector-design-document/) is implemented.
 
 Add a star, show some love :) 

## Questions and Discussion

 * [Djongo groups](https://groups.google.com/d/forum/djongo) is where you can watch for new release announcements, suggest improvements, and discuss topics pertaining to Django and MongoDB.
 * Issues, where things are not working as expected, please raise a git-hub issue ticket. 
 * For questions and clarifications regarding usage, please put it up on stackoverflow instead. 
   
