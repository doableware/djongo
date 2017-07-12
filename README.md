# djongo
Driver for allowing Django to use NoSQL databases

Now use NoSQL databases like Mongodb as a backend for django!!!

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
