# djongo
Driver for allowing Django to use NoSQL databases

Use Mongodb as a backend database for your django project, without changing a single django model!!!

<h2>Usage:</h2>

  1. pip install djongo
  2. Into settings.py file of your project, add: 
  
    DATABASES = {
      'default': {
          'ENGINE': 'djongo',
          'NAME': 'your-db-name',
      }
   }
   
   3. YOUR ARE SET! HAVE FUN!
   
<h2>Requirements:</h2>

  1. djongo requires <b>python 3.5 or above</b>.
  2. MongoDB is a schema free DB, hence manage.py migrate is not needed and not supported.

<h2>How it works:</h2>

  djongo is a SQL to mongodb query complier. It translates every SQL query into a mongoDB query document and quries the backend instance.
  As djongo translates a SQL query string into a MongoDB command, all Django features, models etc work as is.
  
  Django contrib modules: 
  
    'django.contrib.admin',
    'django.contrib.auth',    
    'django.contrib.sessions',
    
 and others... fully supported.
 
 <h2>Questions</h2>
 
   Any questions or issues regarding the usage. Please raise a git-hub issue ticket.
