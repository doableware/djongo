## Todos


## Enhancement requests

### Integers shouldn't play the role of escape hatch. But this is too useful a tool to abandon.
**Contributed by: @techdragon**

In the explanation of https://github.com/nesdis/djongo/issues/36#issue-284738591 the use of `db_column='foo'` was demonstrated on an IntegerField. This was in order to get the raw ObjectID from a mongo document. 

```python
class Foo(models.Model):
   _id = models.IntegerField(db_column='_id')
```

It turns out this works for _any_ field/"column" type. I've subsequently used this to access plain list fields that lack built in support. Going forward this would be a useful escape hatch for any future mongoDB data types that may be added so it should not be replaced by stronger validation of Integers without the introduction of a replacement "escape hatch field type". I'd like to suggest the name "RawField" but its up to you. 😄

### Providing access to the MongoDB ObjectID object of any Djongo Model object instance will improve usefulness.
**Contributed by: @techdragon**


Bypassing limitations in Djongo will typically involve making direct queries to MongoDB. While there is an existing mechanism for this, it lacks the ability to base such queries on data from an existing object. I cannot use Djongo to query an object, then use a decorator/property to perform a specific MongoDB query based on the object I'm currently working with. For example,  simple model query with Djongo, perform complex map reduce with raw `pymongo` via `object.*` where the map reduce requires the ObjectID of the result of the simple query. An alternative example, I want to add a property to my model `Foo` which is the count of all `Bar` models which have an `ObjectID` reference to `Foo` matching a complex criteria expressed with raw `pymongo`.

Requiring the addition of `_id = models.IntegerField(db_column='_id')` wherever we want to have the same ease of use as "regular Django" gives us by using the `self.id` and `self.pk` directly. It can be cloaked behind some `_` property, like `self._mongodb_objectid` or just `self._id`, but either way the usefulness of Djongo would be increased by not having to put `_id = models.IntegerField(db_column='_id')` manually on models.

### Documentation
**Contributed by: @tbobm**

In order to ease a bit contributions, I'd like to make the codebase (which is getting a bit dense), a bit more documented, but I can't do it alone, because there are some parts of the code I don't understand.

Would you mind putting this on the "roadmap"?

As I told you I'd like to contribute to djongo, but there is a lot to discover, and a more verbose code, or a more documented one would greately increase the overwhole attractiveness of extern contributions I think.

Thanks in advance @nesdis ! 😁 

### Simple/Plain arrays of values stored in an Array value are currently unsupported.
**Contributed by: @techdragon**

Ideally, in addition to the existing support for Document Arrays, it would be good to have 'simple' array support. e.g.: Support for https://docs.mongodb.com/manual/tutorial/query-arrays/ in addition to the current support for https://docs.mongodb.com/manual/tutorial/query-array-of-documents/

I can work around this in most circumstances by using the manager query method and properties, but its a hinderance to interoperability with existing MongoDB databases, and could arguably be better. Especially in light of the built in support Django has for PostgreSQL array fields. https://docs.djangoproject.com/en/2.0/ref/contrib/postgres/fields/#arrayfield


### Document how to use Djongo with an existing MongoDB database
**Contributed by: @techdragon**

The documentation already explains how to use djongo so that djongo creates new collections for the django models. However it doesn't have any documentation on how to use djongo with an existing MongoDB collection that already contains documents.

~~Is this possible?~~ [Confirmed as possible](https://github.com/nesdis/djongo/issues/38#issuecomment-354736801)

~~If so,~~ It needs to be documented, ~~if not it would be an extremely useful feature~~.

###  Insert the dictionary(json) in mongodb
**Contributed by: @ravinarayansingh**

 I want to insert the dictionary as the value of the model field. For this, my suggestion is we should have EmbeddedDictField like EmbeddedModelField. I have tried this and it worked.

#### 
apps/models.py
```
data={"name":"xyz","age":12}
year=2017
month=10
class TestModel(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()
    customer = "In this feild i want to store above dictonary"

after having EmbeddedDictField  as type  model will be 
class TestModel(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()
    customer = models.EmbeddedDictField(model_container=dict)
```
 djongo/djongo/models.py
we need to add below  class in   djongo/djongo/models.py
```
djongo/djongo/models.py
class EmbeddedDictField(Field):
    def __init__(self,
                 model_container: typing.Type[dict],
                 model_form_class: typing.Type[forms.ModelForm] = None,
                 model_form_kwargs: dict = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_container = model_container
        self.model_form_class = model_form_class
        self.null = True
        self.instance = None

        if model_form_kwargs is None:
            model_form_kwargs = {}
        self.model_form_kwargs = model_form_kwargs

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['model_container'] = self.model_container
        if self.model_form_class is not None:
            kwargs['model_form_class'] = self.model_form_class
        return name, path, args, kwargs

    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname)
        # print(value)
        ret_val = {}
        # for fld in value._meta.get_fields():
        #     if not useful_field(fld):
        #         continue
        #
        #     fld_value = getattr(value, fld.attname)
        # ret_val[ self.attname] = fld.get_db_prep_value(value, None, False)
        ret_val[self.attname] = self.get_db_prep_value(value, None, False)
        return ret_val

    def get_db_prep_value(self, value, connection=None, prepared=False):
        if isinstance(value, dict):
            return value

        if not isinstance(value, Model):
            raise TypeError('Object must be of type Model')

        mdl_ob = {}
        for fld in value._meta.get_fields():
            if not useful_field(fld):
                continue
            fld_value = getattr(value, fld.attname)
            mdl_ob[fld.attname] = fld.get_db_prep_value(fld_value, connection, prepared)

        return mdl_ob

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)
```

so that we can create the model
tree = TestModel(year=year,month=month,customer =data)
tree.save()
