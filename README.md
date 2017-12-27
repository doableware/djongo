<h1>djongo</h1>
<h2>Driver for allowing Django to use MongoDB as the database backend</h2>

Use MongoDB as a backend database for your Django project, without changing the Django ORM. Use the Django Admin GUI to add and modify documents in MongoDB. 

<h2>Usage:</h2>
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
   <li> Run <code>manage.py makemigrations <app_name></code> followed by <code>manage.py migrate</code> (ONLY the first time to create collections in mongoDB) </li>
   <li> YOUR ARE SET! HAVE FUN! </li>
</ol>
<h2>Requirements:</h2>

  1. Python 3.6 or higher.
  2. MongoDB 3.4 or higher.
  3. If your models use nested queries or sub querysets like:
  
      ```python
      inner_qs = Blog.objects.filter(name__contains='Ch').values('name')
      entries = Entry.objects.filter(blog__name__in=inner_qs)
      ```
     MongoDB 3.6 or higher is required.


<h2>How it works:</h2>

djongo is a SQL to mongodb query compiler. It translates a SQL query string into a mongoDB query document. As a result, all Django features, models etc work as is.
  
  Django contrib modules: 
<pre><code>  
'django.contrib.admin',
'django.contrib.auth',    
'django.contrib.sessions',

</code></pre>
 and others... fully supported.

## Top Star Contributors

[Rudolfce](https://github.com/rudolfce)

<h2>Features:</h2>

  * Stop the immigrations.  
  * Use Django Admin GUI to access MongoDB  
  * Embedded model.
  * Embedded Array.
  * Embedded Form Fields.
  
  Read the [full documentation](https://nesdis.github.io/djongo/)

 <h2>Questions</h2>
 
   Suggestions for improvements or issues, please raise a git-hub issue ticket. For questions and clarifications regarding usage, please put it up on stackoverflow instead. 
   
 ## Contribute
 
 If you think djongo is useful, **please share it** with the world! Your endorsements and online reviews will help get more support for this project.
  
 You can contribute to the source code or the documentation by creating a simple pull request! You may want to refer to the design documentation to get an idea on how [Django MongoDB connector](https://nesdis.github.io/djongo/django-mongodb-connector-design-document/) is implemented.
 
 Add a star, show some love :)
