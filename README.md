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
With username and password
DATABASES = {
 'default': {
    'ENGINE': 'djongo',
    'NAME': 'your-db-name'),
    'HOST': 'host-name ot ip address',
    'PORT': port-number,
    'USER': 'db-username',
    'PASSWORD': 'password',
    'AUTH_SOURCE': 'db-name',
    'AUTH_MECHANISM': 'SCRAM-SHA-1',
     
 }`
}
```
</li>   
   <li> Run <code>manage.py makemigrations</code> followed by <code>manage.py migrate</code> (ONLY the first time to create collections in mongoDB) </li>
   <li> YOUR ARE SET! HAVE FUN! </li>
</ol>
<h2>Requirements:</h2>

  1. djongo requires <b>python 3.6 or above.</b>


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
 
   Any questions, suggestions for improvements or issues regarding the usage. Please raise a git-hub issue ticket.
   
 ## Contribute
 
 If you think djongo is useful, **please share it** with the world! Your endorsements and online reviews will help get more support for this project.
  
 You can contribute to the source code or the documentation by creating a simple pull request! You may want to refer to the design documentation to get an idea on how [Django MongoDB connector](https://nesdis.github.io/djongo/django-mongodb-connector-design-document/) is implemented.
 
 Add a star, show some love :)
