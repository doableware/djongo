<h1>djongo</h1>

<a href="https://opensource.org/licenses/BSD-3-Clause"><img src="https://img.shields.io/badge/License-BSD%203--Clause-blue.svg" alt="BSD3" height="18"></a>
<a href="https://badge.fury.io/py/djongo"><img src="https://badge.fury.io/py/djongo.svg" alt="PyPI version" height="18"></a>

<h2>Driver for allowing Django to use MongoDB as the database backend</h2>


Use MongoDB as a backend database for your Django project, without changing the Django ORM. Use the Django Admin GUI to add and modify documents in MongoDB. 

## Usage:
<ol>
<li> pip install djongo </li>
<li> Into settings.py file of your project, add: 

``` 
DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': 'your-db-name',
    }`
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

  * Stop the immigrations.  
  * Use Django Admin GUI to access MongoDB.  
  * Embedded Model.
  * Embedded Array.
  * Embedded Form Fields.
  
  Read the [full documentation](https://nesdis.github.io/djongo/)
  
## Contribute
 
 If you think djongo is useful, **please share it** with the world! Your endorsements and online reviews will help get more support for this project.
  
 The [roadmap](https://nesdis.github.io/djongo/roadmap/) document contains a list of features that must be implemented in future versions of Djongo. You can contribute to the source code or the documentation by creating a simple pull request! You may want to refer to the design documentation to get an idea on how [Django MongoDB connector](https://nesdis.github.io/djongo/django-mongodb-connector-design-document/) is implemented.
 
 Add a star, show some love :) 
 
## Top Star Contributors

[Rudolfce](https://github.com/rudolfce)

## Questions
 
   Suggestions for improvements or issues, please raise a git-hub issue ticket. For questions and clarifications regarding usage, please put it up on stackoverflow instead. 
   
