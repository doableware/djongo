# djongo
Driver for allowing Django to use NoSQL databases

Use Mongodb as a backend database for your django project, without changing a single django model!!!

<h2>Usage:</h2>

  1. Clone djongo directory into Lib\site-packages\django\db\backends
  2. Add: 
  
    DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.djongo',
          'NAME': 'your-db-name',
      }
   }
   
   Into settings.py file of your project.
   
   3. YOUR ARE SET! HAVE FUN!

<h2>How it works:</h2>

  djongo is a SQL to mongodb query complier. It translates every SQL query into a mongoDB query document and quries the backend instance.
  As djongo translates a SQL query string into a MongoDB command, all Django features, models etc work as is.
  
  Django contrib modules: 
  
    'django.contrib.admin',
    'django.contrib.auth',    
    'django.contrib.sessions',
    
 and others... fully supported.
