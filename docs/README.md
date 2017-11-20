# Django and MongoDB database connector
Use Mongodb as a backend database for your django project, without changing a single django model!!!

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
 
For a more detailed discussion on usage with Django check out [Integrating Django with MongoDB](/djongo/integrating-django-with-mongodb/)

## Use the Admin GUI to add 'embedded' documents

<div style="max-width: 95%; margin-left: auto; margin-right: auto">
    <img src="/djongo/images/admin.jpg" alt="Django Admin">
</div>
   
### The Embedded Model
 
SQL prevents the usage of embedded objects in your models without serialization. <b>Not anymore.</b> With mongoDB as your django backend, embed any other model into your parent model and save it as an [embedded document](https://docs.mongodb.com/manual/core/data-model-design/#data-modeling-embedding) into mongoDB

Define the model to embed into parent model, like any Django model:

```python
from djongo import models

class BlogContent(models.Model):
    comment = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    class Meta:
        abstract = True
```

In case you dont plan on using your embedded model as a standalone model (which means it will always be embedded inside a parent model) you should add the `class Meta` and `abstract = True` as shown above. This way Djongo will never register this model as an [actual model](https://docs.djangoproject.com/en/dev/topics/db/models/#abstract-base-classes).

It is always a good practice to **make embedded models as abstract models** and this is **strongly recommended**.

#### EmbeddedModelField

Embed the above model inside the parent model by creating an `EmbeddedModelField`. The `EmbeddedModelField` is similar to other Django Fields (like the `CharField`.)

```python
class EmbeddedModelField(Field):
    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form: typing.Optional[Type[forms.ModelForm]]=None,
                 model_form_kwargs: typing.Optional[dict]=None,
                 *args, **kwargs):
```

##### Parameters

  * `model_container: Type[models.Model]` The child model class type (not instance) that this embedded field will contain.
  * `model_form: Optional[Type[models.forms.ModelForm]]` The child model form class type of the embedded model.
  * `model_form_kwargs: Optional[dict]` The kwargs (if any) that must be passed to the embedded model form while instantiating it.
  
##### Example

```python
class BlogContentForm(forms.ModelForm):
    class Meta:
        model = BlogContent
        fields = (
            'comment', 'author'
        )


class BlogContent(models.Model):
    comment = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    class Meta:
        abstract = True
        

class BlogPost(models.Model):
    h1 = models.CharField(max_length=100)
    content = models.EmbeddedModelField(
        model_container=BlogContent,
        model_form=BlogContentForm
    )
    
    objects = models.DjongoManager()
```

### Embedded Array

With MongoDB there can be an [array](https://docs.mongodb.com/manual/core/document/#arrays) of embedded documents inside the parent document. You can create an **embed array/list of models inside the parent model** and store it directly into MongoDB.

Define the model to embed into parent model, like any Django model:

```python
from djongo import models

class BlogContent(models.Model):
    comment = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    class Meta:
        abstract = True
```

#### ArrayModelField
Create an array of the above child model inside the parent model by creating an `ArrayModelField`. The `ArrayModelField` is similar to other Django Fields (like the `CharField`.)

```python
class ArrayModelField(Field):
    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form: typing.Type[forms.ModelForm]=None,
                 model_form_kwargs_l: dict=None,
                 *args, **kwargs):
```

##### Parameters

  * `model_container: Type[models.Model]` The child model class type (not instance) that this array field will contain.
  * `model_form: Optional[Type[models.forms.ModelForm]]` The child model form class type of the array model. All child models inside the array must be of the same type. Mixing different types of child models inside the embedded array is not supported.
  * `model_form_kwargs: Optional[dict]` The kwargs (if any) that must be passed to the embedded model form while instantiating it.
  
##### Example

```python
class BlogContentForm(forms.ModelForm):
    class Meta:
        model = BlogContent
        fields = (
            'comment', 'author'
        )


class BlogContent(models.Model):
    comment = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    class Meta:
        abstract = True
        
        
class BlogPost(models.Model):
    h1 = models.CharField(max_length=100)
    content = models.ArrayModelField(
        model_container=BlogContent,
        model_form=BlogContentForm
    )
    
    objects = models.DjongoManager()
```

### Embedded Form

Embed multiple sub-forms, inside the parent form. Directly translate it into an embedded model and `.save()` it into mongoDB. No foreign key lookups necessary!

<pre><code>
Name:
Address:
    No:
    Street:
Phone:
    Landline:
    Mobile:

</code></pre>

While creating a Form from a Model [the ModelForm](https://docs.djangoproject.com/en/dev/topics/forms/modelforms/) the embedded form **gets automatically generated** if the Model contains an embedded model inside it.

Multiple embedded forms get automatically generated when the Model contains an array of embedded models.

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

