<h1>djongo</h1>
<h2>Driver for allowing Django to use NoSQL/MongoDB databases</h2>

Use Mongodb as a backend database for your django project, without changing a single django model!!!

<h2>Usage:</h2>
<ol>
<li> pip install djongo </li>
<li> Into settings.py file of your project, add: 
<pre><code>  
DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': 'your-db-name',
    }
}

</code></pre>
</li>   
   <li> Run <code>manage.py migrate</code> (ONLY the first time to create collections in mongoDB) </li>
   <li> YOUR ARE SET! HAVE FUN! </li>
</ol>
<h2>Requirements:</h2>

  1. djongo requires <b>python 3.5 or above</b>.


<h2>How it works:</h2>

  djongo is a SQL to mongodb query complier. It translates every SQL query into a mongoDB query document and quries the backend instance.
  As djongo translates a SQL query string into a MongoDB command, all Django features, models etc work as is.
  
  Django contrib modules: 
<pre><code>  
'django.contrib.admin',
'django.contrib.auth',    
'django.contrib.sessions',

</code></pre>
 and others... fully supported.
 
 <h2>Features:</h2>
 <h3>Stop the immigrations</h3>
    <p>MongoDB is a schema free DB. You no longer need to run <code> manage.py migrate</code> every time you change a model.</p>
 <h3>Embedded model</h3>
    <p>SQL prevents the usage of embedded objects in your models without serialization. <b>Not any more.</b> With mongoDB as your django backend, embed any other model into your parent model and save it as an embedded doucument into mongoDB</p>

<pre><code>    
from djongo import models

class BlogContent(models.Model):
    comment = models.CharField(max_length=100)
    author = models.CharField(max_length=100)

class BlogPost(models.Model):
    h1 = models.CharField(max_length=100)
    content = models.EmbeddedModelField(
        model_container=BlogContent,
        model_form=BlogContentForm
    )
</code></pre>

 <h3>Embedded Array</h3>
    <p>MongoDB allows array of embedded documents inside the parent document. You can create an <b>array(list) of embedded models inside the parent model</b> and store it directly into mongoDB.</p>

<pre><code>
class BlogPage(models.Model):
    title = models.CharField(max_length=100)
    blog_posts = models.ArrayModelField(
      model_container=BlogPost,
      model_form=BlogPostForm      
    )

    objects = models.DjongoManager()
</code></pre>
        
 <h3>Embedded Form Fields</h3>
    <p>Embed multiple sub-forms, inside the parent form. Directly translate it into an embedded model and <code>.save()</code> it into mongoDB. No foriegn key lookups necessary!</p>
<pre><code>   
Name:
Address:
    No:
    Street:
Phone:
    Landline:
    Mobile:
        
</code></pre>    
 <h2>Questions</h2>
 
   Any questions or issues regarding the usage. Please raise a git-hub issue ticket.
