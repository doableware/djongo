# djongo
<h1>Driver for allowing Django to use NoSQL/MongoDB databases</h1>

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
   
   3. Run manage.py migrate (ONLY the first time to create collections in mongoDB)
   4. YOUR ARE SET! HAVE FUN!
   
<h2>Requirements:</h2>

  1. djongo requires <b>python 3.5 or above</b>.


<h2>How it works:</h2>

  djongo is a SQL to mongodb query complier. It translates every SQL query into a mongoDB query document and quries the backend instance.
  As djongo translates a SQL query string into a MongoDB command, all Django features, models etc work as is.
  
  Django contrib modules: 
  
    'django.contrib.admin',
    'django.contrib.auth',    
    'django.contrib.sessions',
    
 and others... fully supported.
 
 <h2>Features:</h2>
 <h3>Stop the immigrations</h3>
    <p>MongoDB is a schema free DB. You no longer need to run <code> manage.py migrate</code> every time you change a model.</p>
 <h3>Embedded model</h3>
    <p>SQL prevents the usage of embedded objects in your models without serialization. <b>Not any more.</b> With mongoDB as your django backend, embed any other model into your parent model and save it as an embedded doucument into mongoDB</p>
 <h3>Embedded Array</h3>
    <p>MongoDB allows array of embedded documents inside the parent document. You can create an <b>array(list) of embedded models inside the parent model</b> and store it directly into mongoDB.
 <h3>Embedded Form Fields</h3>
    <p>Embed multiple sub-forms, inside the parent form. Directly translate it into an embedded model and <code>.save()</code> it into mongoDB. No foriegn key lookups necessary!</p>
    
    Name:
    Address:
        No:
        Street:
    Phone:
        Landline:
        Mobile:
    
 <h2>Questions</h2>
 
   Any questions or issues regarding the usage. Please raise a git-hub issue ticket.
