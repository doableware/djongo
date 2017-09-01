Use Mongodb as a backend database for your django project, without changing a single django model!!!

# Usage
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

# Requirements

  1. djongo requires <b>python 3.5 or above</b>.


# How it works

  djongo is a SQL to mongodb query compiler. It translates a SQL query string into a mongoDB query document. As a result, all Django features, models etc work as is.
  
  Django contrib modules: 
<pre><code>  
'django.contrib.admin',
'django.contrib.auth',    
'django.contrib.sessions',

</code></pre>
 and others... fully supported.
 
# Integration with Django

## Reuse Django Models
 
 Django is a stable framework with continuous development and enhancements. The Django ORM is quite extensive and feature rich. Defining *another* ORM to work with MongoDB means reproducing the entire Django ORM again. The new ORM needs to constantly align with the Django ORM. The idea behind Djongo is to **reuse** existing Django ORM features by finally translating SQL queries to MongoDB syntax. 
 
 As **SQL syntax will never change** regardless of future additions to Django, by using Djongo your code is now future proof!  
  
## Stop the immigrations
 
  MongoDB is a schema free DB. You no longer need to run <code> manage.py migrate</code> every time you change a model. Making changes to your models is easier.
    
# Embedded Model
 
SQL prevents the usage of embedded objects in your models without serialization. <b>Not anymore.</b> With mongoDB as your django backend, embed any other model into your parent model and save it as an embedded document into mongoDB

Define the model to embed into parent model, like any Django model:

```python
from djongo import models

class BlogContent(models.Model):
    comment = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    class Meta:
        abstract = True
```

In case you dont plan on using your embedded model as a standalone model (which means it will always be embedded inside a parent model) you should add the `class Meta` and `abstract = True` as shown above. This way Djongo will never register this model as an [actual model](https://docs.djangoproject.com/en/1.11/topics/db/models/#abstract-base-classes).

It is always a good practice to **make embedded models as abstract models** and this is strongly recommended.

## EmbeddedModelField

Embed the above model inside the parent model by creating an `EmbeddedModelField`. The `EmbeddedModelField` is similar to other Django Fields (like the `CharField`.)

```python
class EmbeddedModelField(Field):
    def __init__(self,
                 model_container: Type[Model],
                 model_form: Optional[Type[forms.ModelForm]]=None,
                 model_form_kwargs: Optional[dict]=None,
                 *args, **kwargs):
```

### Parameters

  * `model_container: models.Model` The child model class type (not instance) that this embedded field will contain.
  * `model_form: Optional[models.forms.ModelForm]` The child model form class type of the embedded model.
  * `model_form_kwargs: Optional[dict]` The kwargs (if any) that must be passed to the embedded model form while instantiating it.
  
### Example:
```python
class BlogContentForm(forms.ModelForm):
    class Meta:
        model = BlogContent
        fields = (
            'comment', 'author'
        )


class BlogPost(models.Model):
    h1 = models.CharField(max_length=100)
    content = models.EmbeddedModelField(
        model_container=BlogContent,
        model_form=BlogContentForm
    )
```



<script>
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-75159067-1', 'auto');
  ga('send', 'pageview');

</script>

