<h1>djongo</h1>
<h2>Driver for allowing Django to use NoSQL/MongoDB databases</h2>

Use Mongodb as a backend database for your django project, without changing a single django model!!!

<h2>Usage:</h2>
<ol>
<li> pip install djongo </li>
<li> Into settings.py file of your project, add: 

``` 
DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': 'your-db-name',
    }
}
```
</li>   
   <li> Run <code>manage.py migrate</code> (ONLY the first time to create collections in mongoDB) </li>
   <li> YOUR ARE SET! HAVE FUN! </li>
</ol>
<h2>Requirements:</h2>

  1. djongo requires <b>python 3.5 or above.</b>


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

[rudolfce](https://github.com/rudolfce)

<h2>Features:</h2>

  * Stop the immigrations.    
  * Embedded model.
  * Embedded Array.
  * Embedded Form Fields.
  
  Read the [full documentation](https://nesdis.github.io/djongo/)

 <h2>Questions</h2>
 
   Any questions, suggestions for improvements or issues regarding the usage. Please raise a git-hub issue ticket.
   
 ## Contribute
 
 If you think djongo is cool, **don't feel shy to share it** with the world! Happiness increases with sharing.
