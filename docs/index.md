---
title: Django and MongoDB connector
permalink: "/"
---


Use MongoDB as a backend database for your Django project, without changing the Django ORM. Use the Django Admin app to add and modify documents in MongoDB. 

## Usage

1. pip install djongo
2. Into `settings.py` file of your project, add:

      ```python
      DATABASES = {
          'default': {
              'ENGINE': 'djongo',
              'NAME': 'your-db-name',
          }
      }
      ```
  
3. Run `manage.py makemigrations <app_name>` followed by `manage.py migrate` (ONLY the first time to create collections in MongoDB)
4. YOUR ARE SET! HAVE FUN!

## Requirements

1. Python 3.6 or higher.
2. MongoDB 3.4 or higher.
3. If your models use nested queries or sub querysets like:
  
      ```python
      inner_qs = Blog.objects.filter(name__contains='Ch').values('name')
      entries = Entry.objects.filter(blog__name__in=inner_qs)
      ```
     MongoDB 3.6 or higher is required.


## How it works

Djongo is a SQL to MongoDB query compiler. It translates a SQL query string into a [MongoDB query document](https://docs.mongodb.com/manual/tutorial/query-documents/). As a result, all Django features, models, etc., work as is.
  
Django contrib modules: 

```python
'django.contrib.admin',
'django.contrib.auth',    
'django.contrib.sessions',
```
and others... fully supported.
  
## Usage with Django

Djongo connector for MongoDB ensures that you:

 * Reuse Django Models/ORM
 * Work with the original Django variant
 * Future proof your code
 * Atomic SQL JOIN operations
 
Refer to [Integrating Django with MongoDB](/djongo/integrating-django-with-mongodb/) for the detailed reference.

## Use the Admin GUI to add embedded documents

Let’s say you want to create a blogging platform using Django with MongoDB as your backend.
In your Blog `app/models.py` file define the `BlogContent` model:

```python
from djongo import models
from djongo.models import forms
class BlogContent(models.Model):
    comment = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    class Meta:
        abstract = True
```

To access the model using Django Admin you will need a Form definition for the above model. Define it as below:

```python
class BlogContentForm(forms.ModelForm):

    class Meta:
        model = BlogContent
        fields = (
            'comment', 'author'
        )
```

Now ‘embed’ your `BlogContent` inside a `BlogPost` using the `EmbeddedModelField`:

```python
class BlogPost(models.Model):
    h1 = models.CharField(max_length=100)
    content = models.EmbeddedModelField(
        model_container=BlogContent,
        model_form_class=BlogContentForm
    )   
```

That’s it you are set! Fire up Django Admin on localhost:8000/admin/ and this is what you get:


![Django Admin](/djongo/assets/images/admin.jpg)


### Querying Embedded fields

In the above example to query all BlogPost with content made by authors whose name startswith 'Paul'  use the following query:

```python
entries = BlogPost.objects.filter(content__startswith={'author': 'Paul'})
```

Refer to [Using Django with MongoDB data fields](/djongo/using-django-with-mongodb-data-fields/) for more details.

## Djongo Manager
 The Djongo Manager extends the  functionality of the usual [Django Manager](https://docs.djangoproject.com/en/dev/topics/db/managers/). Define your manager as Djongo Manager in the model.

 ```python
class BlogPost(models.Model):
    h1 = models.CharField(max_length=100)
    objects = models.DjongoManager()
```

Use it like the usual Django manager:

```python
post = BlogPost.objects.get(pk=p_key)
```

Will [get a model object](https://docs.djangoproject.com/en/dev/topics/db/queries/#retrieving-a-single-object-with-get) having primary key `p_key`.

### Tunnel directly to Pymongo 

MongoDB has powerful query syntax and `DjongoManager` lets you exploit it fully.

```python
class BlogView(DetailView):

    def get_object(self, queryset=None):
        index = [i for i in BlogPost.objects.mongo_aggregate([
            {
                '$match': {
                    'title': self.kwargs['path']
                }
            },
            {
                '$project': {
                    '_id': 0,
                }
            }
        ])]

        return index

```

You can directly *access any [pymongo](https://api.mongodb.com/python/current/) command* by prefixing `mongo_` to the command name. Eg. to perform `aggregate` on the BlogPage collection (BlogPage is stored as a table in SQL or a collection in MongoDB) the function name becomes `mongo_aggregate`. To directly insert a document (instead of `.save()` a model) use `mongo_insert_one()`

## Questions
 
Any questions, suggestions for improvements, issues regarding the usage or to contribute to the package, please raise a git-hub issue ticket.

## Contribute
 
 If you think djongo is useful, **please share it** with the world! Your endorsements and online reviews will help get more support for this project.
  
 The [roadmap](https://nesdis.github.io/djongo/roadmap/) document contains a list of features that must be implemented in future versions of Djongo. You can contribute to the source code or the documentation by creating a simple pull request! You may want to refer to the design documentation to get an idea on how [Django MongoDB connector](https://nesdis.github.io/djongo/django-mongodb-connector-design-document/) is implemented.
 
<script>
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-75159067-1', 'auto');
  ga('send', 'pageview');

</script>

