# Django and MongoDB database connector
Use MongoDB as a backend database for your Django project, without changing the Django ORM. Use the Django Admin app to add and modify documents in MongoDB. 

## Usage

1. pip install djongo
2. Into settings.py file of your project, add:

    ```python
    DATABASES = {
        'default': {
            'ENGINE': 'djongo',
            'NAME': 'your-db-name',
        }
    }
    ```
  
3. Run `manage.py makemigrations` followed by `manage.py migrate` (ONLY the first time to create collections in mongoDB)
4. YOUR ARE SET! HAVE FUN!

## Requirements

  1. djongo requires <b>python 3.6 or above</b>.


## How it works

djongo is a SQL to MongoDB query compiler. It translates a SQL query string into a [mongoDB query document](https://docs.mongodb.com/manual/tutorial/query-documents/). As a result, all Django features, models, etc., work as is.
  
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
 * Stop the immigrations 
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

To access the model using Django Admin you will need a Form definition for the above model. Define it as shown below:

```python
class BlogContentForm(forms.ModelForm):

    class Meta:
        model = BlogContent
        fields = (
            'comment', 'author'
        )
```

Now ‘embed’ your `BlogContent` inside a `BlogPost` using the `EmbeddedModelField` as below:

```python
class BlogPost(models.Model):
    h1 = models.CharField(max_length=100)
    content = models.EmbeddedModelField(
        model_container=BlogContent,
        model_form_class=BlogContentForm
    )   
```

That’s it you are set! Fire up Django Admin on localhost:8000/admin/ and this is what you get:

<div style="max-width: 100%; margin-left: auto; margin-right: auto">
    <img src="/djongo/images/admin.jpg" alt="Django Admin">
</div>
   
Next, assume you want to ‘extend’ the author field to contain more than just the name. You need both a name and email. Simply make the author field an ‘embedded’ field instead of a ‘char’ field:

```python
class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100)

    class Meta:
        abstract = True


class AuthorForm(forms.ModelForm):

    class Meta:
        model = Author
        fields = (
            'name', 'email'
        )

class BlogContent(models.Model):
    comment = models.CharField(max_length=100)
    author = models.EmbeddedModelField(
        model_container=Author,
        model_form_class=AuthorForm
    )
    class Meta:
        abstract = True
```   

If a blog post has multiple content from multiple authors, define a new model:

```python
class MultipleBlogPosts(models.Model):
    h1 = models.CharField(max_length=100)
    content = models.ArrayModelField(
        model_container=BlogContent,
        model_form_class=BlogContentForm
    )
```
Fire up Django Admin with the new changes and you have:

<div style="max-width: 100%; margin-left: auto; margin-right: auto">
    <img src="/djongo/images/admin-extended.jpg" alt="Django Admin">
</div>

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

### Direct pymongo access

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
 
You can contribute to the source code or the documentation by creating a simple pull request! You may want to refer to the design documentation to get an idea on how [Django MongoDB connector](https://nesdis.github.io/djongo/django-mongodb-connector-design-document/) is implemented.
 
<script>
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-75159067-1', 'auto');
  ga('send', 'pageview');

</script>

