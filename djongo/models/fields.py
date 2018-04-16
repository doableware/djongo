"""
The standard way of using djongo is to import models.py
in place of Django's standard models module.

Djongo Fields is where custom fields for working with
MongoDB is defined.

 - EmbeddedModelField
 - ArrayModelField
 - ArrayReferenceField
 - GenericReferenceField

These are the main fields for working with MongoDB.
"""

from bson import ObjectId
from django.db.models import (
    Manager, Model, Field, AutoField,
    ForeignKey, CASCADE, BigAutoField
)
from django import forms
from django.core.exceptions import ValidationError
from django.db import router
from django.db import connections as pymongo_connections
import typing
import functools

from django.db.models.fields.mixins import FieldCacheMixin
from django.forms import modelform_factory
from django.utils.html import format_html_join, format_html
from pymongo.collection import Collection

from django.db.models.fields.related import RelatedField
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor, ManyToManyDescriptor, \
    create_forward_many_to_many_manager, ReverseManyToOneDescriptor
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe


def make_mdl(model, model_dict):
    """
    Builds an instance of model from the model_dict.
    """
    for field_name in model_dict:
        field = model._meta.get_field(field_name)
        model_dict[field_name] = field.to_python(model_dict[field_name])

    return model(**model_dict)


def useful_field(field):
    return field.concrete and not (field.is_relation
                                   or isinstance(field, (AutoField, BigAutoField)))


class ModelSubterfuge:

    def __init__(self, embedded_model):
        self.subterfuge = embedded_model


class DjongoManager(Manager):
    """
    This modified manager allows to issue Mongo functions by prefixing
    them with 'mongo_'.

    This module allows methods to be passed directly to pymongo.
    """
    def __getattr__(self, name):
        if name.startswith('mongo'):
            name = name[6:]
            cli = (
                pymongo_connections[self.db]
                .cursor()
                .db_conn[self.model
                         ._meta.db_table]
            )
            return getattr(cli, name)
        else:
            return super().__getattr__(name)


class ListField(Field):
    """
    MongoDB allows the saving of arbitrary data inside it's embedded array. The `ListField` is useful in such cases.
    """
    empty_strings_allowed = False

    def __init__(self, *args, **kwargs):
        self._value = []
        super().__init__(*args, **kwargs)

    def __set__(self, instance, value):
        if not isinstance(value, list):
            raise ValueError('Value must be a list')

        self._value = value

    def __get__(self, instance, owner):
        return self._value

    def get_db_prep_value(self, value, connection, prepared=False):
        if prepared:
            return value

        if not isinstance(value, list):
            raise ValueError('Value must be a list')

        return value


class ArrayModelField(Field):
    """
    Implements an array of objects inside the document.

    The allowed object type is defined on model declaration. The
    declared instance will accept a python list of instances of the
    given model as its contents.

    The model of the container must be declared as abstract, thus should
    not be treated as a collection of its own.

    Example:

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

    class MultipleBlogPosts(models.Model):
        h1 = models.CharField(max_length=100)
        content = models.ArrayModelField(
            model_container=BlogContent,
            model_form_class=BlogContentForm
        )

    """

    empty_strings_allowed = False

    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form_class: typing.Type[forms.ModelForm] = None,
                 model_form_kwargs_l: dict = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_container = model_container
        self.model_form_class = model_form_class

        if model_form_kwargs_l is None:
            model_form_kwargs_l = {}
        self.model_form_kwargs_l = model_form_kwargs_l

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['model_container'] = self.model_container

        if self.model_form_class is not None:
            kwargs['model_form_class'] = self.model_form_class

        if self.model_form_kwargs_l:
            kwargs['model_form_kwargs_l'] = self.model_form_kwargs_l

        return name, path, args, kwargs

    def get_db_prep_value(self, value, connection, prepared=False):
        if prepared:
            return value

        if not isinstance(value, list):
            raise ValueError('Value must be a list')

        ret = []
        for a_mdl in value:
            mdl_ob = {}
            if not isinstance(a_mdl, Model):
                raise ValueError('Array items must be Model instances')
            for fld in a_mdl._meta.get_fields():
                if not useful_field(fld):
                    continue
                fld_value = getattr(a_mdl, fld.attname)
                mdl_ob[fld.attname] = fld.get_db_prep_value(fld_value, connection, prepared)
            ret.append(mdl_ob)

        return ret

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        """
        Overrides standard to_python method from django models to allow
        correct translation of Mongo array to a python list.
        """
        if value is None:
            return value

        assert isinstance(value, list)
        ret = []
        for mdl_dict in value:
            if isinstance(mdl_dict, self.model_container):
                ret.append(mdl_dict)
                continue
            mdl = make_mdl(self.model_container, mdl_dict)
            ret.append(mdl)

        return ret

    def formfield(self, **kwargs):
        """
        Returns the formfield for the array.
        """
        defaults = {
            'form_class': ArrayFormField,
            'model_container': self.model_container,
            'model_form_class': self.model_form_class,
            'name': self.attname,
            'mdl_form_kw_l': self.model_form_kwargs_l

        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        errors = []
        for mdl in value:
            try:
                mdl.full_clean()
            except ValidationError as e:
                errors.append(e)
        if errors:
            raise ValidationError(errors)


def _get_model_form_class(model_form_class, model_container, admin, request):
    if not model_form_class:
        form_kwargs = dict(
            form=forms.ModelForm,
            fields=forms.ALL_FIELDS,
        )

        if admin and request:
            form_kwargs['formfield_callback'] = functools.partial(
                admin.formfield_for_dbfield, request=request)

        model_form_class = modelform_factory(model_container, **form_kwargs)

    return model_form_class


class ArrayFormField(forms.Field):
    def __init__(self, name, model_form_class, model_container, mdl_form_kw_l,
                 widget=None, admin=None, request=None, *args, **kwargs):

        self.name = name
        self.model_container = model_container
        self.model_form_class = _get_model_form_class(
            model_form_class, model_container, admin, request)
        self.mdl_form_kw_l = mdl_form_kw_l
        self.admin = admin
        self.request = request

        if not widget:
            widget = ArrayFormWidget(self.model_form_class.__name__)

        error_messages = {
            'incomplete': 'Enter all required fields.',
        }

        self.ArrayFormSet = forms.formset_factory(
            self.model_form_class, can_delete=True)
        super().__init__(error_messages=error_messages,
                         widget=widget, *args, **kwargs)

    def clean(self, value):
        if not value:
            return []

        form_set = self.ArrayFormSet(value, prefix=self.name)
        if form_set.is_valid():
            ret = []
            for itm in form_set.cleaned_data:
                if itm.get('DELETE', True):
                    continue
                itm.pop('DELETE')
                ret.append(self.model_form_class._meta.model(**itm))
            return ret

        else:
            raise ValidationError(form_set.errors + form_set.non_form_errors())

    def has_changed(self, initial, data):
        form_set_initial = []
        for init in initial:
            form_set_initial.append(
                forms.model_to_dict(
                    init,
                    fields=self.model_form_class._meta.fields,
                    exclude=self.model_form_class._meta.exclude
                )
            )
        form_set = self.ArrayFormSet(data, initial=form_set_initial, prefix=self.name)
        return form_set.has_changed()

    def get_bound_field(self, form, field_name):
        return ArrayFormBoundField(form, self, field_name)


class ArrayFormBoundField(forms.BoundField):
    def __init__(self, form, field, name):
        super().__init__(form, field, name)

        data = self.data if form.is_bound else None
        initial = []
        if self.initial is not None:
            for ini in self.initial:
                if isinstance(ini, Model):
                    initial.append(
                        forms.model_to_dict(
                            ini,
                            fields=field.model_form_class._meta.fields,
                            exclude=field.model_form_class._meta.exclude
                        ))

        self.form_set = field.ArrayFormSet(data, initial=initial, prefix=name)

    def __getitem__(self, idx):
        if not isinstance(idx, (int, slice)):
            raise TypeError
        return self.form_set[idx]

    def __iter__(self):
        for form in self.form_set:
            yield form

    def __str__(self):
        table = format_html_join(
            '\n','<tbody>{}</tbody>',
            ((form.as_table(),)
             for form in self.form_set))
        table = format_html(
            '\n<table class="{}-array-model-field">'
            '\n{}'
            '\n</table>',
            self.name,
            table)
        return format_html('{}\n{}',table, self.form_set.management_form)

    def __len__(self):
        return len(self.form_set)


class ArrayFormWidget(forms.Widget):
    def __init__(self, first_field_id, attrs=None):
        self.first_field_id = first_field_id
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        assert False

    def id_for_label(self, id_):
        return '{}-0-{}'.format(id_, self.first_field_id)

    def value_from_datadict(self, data, files, name):
        ret = {key: data[key] for key in data if key.startswith(name)}
        return ret

    def value_omitted_from_data(self, data, files, name):
        for key in data:
            if key.startswith(name):
                return False
        return True


class EmbeddedModelField(Field):
    """
    Allows for the inclusion of an instance of an abstract model as
    a field inside a document.

    Example:

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

    class MultipleBlogPosts(models.Model):
        h1 = models.CharField(max_length=100)
        content = models.ArrayModelField(
            model_container=BlogContent,
            model_form_class=BlogContentForm
        )

    """
    empty_strings_allowed = False

    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form_class: typing.Type[forms.ModelForm]=None,
                 model_form_kwargs: dict=None,
                 admin=None,
                 request=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_container = model_container
        self.model_form_class = model_form_class
        self.null = True
        self.instance = None
        self.admin = admin
        self.request = request

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
        if isinstance(value, ModelSubterfuge):
            return value

        subterfuge = ModelSubterfuge(value)
        # setattr(model_instance, self.attname, subterfuge)
        return subterfuge

    def get_db_prep_value(self, value, connection=None, prepared=False):
        if isinstance(value, dict):
            return value
        if isinstance(value, ModelSubterfuge):
            value = value.subterfuge

        if not isinstance(value, Model):
            raise ValueError('Value must be instance of Model')

        mdl_ob = {}
        for fld in value._meta.get_fields():
            if not useful_field(fld):
                continue
            fld_value = getattr(value, fld.attname)
            mdl_ob[fld.attname] = fld.get_db_prep_value(fld_value, connection, prepared)

        return mdl_ob

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        """
        Overrides Django's default to_python to allow correct
        translation to instance.
        """
        if value is None or isinstance(value, self.model_container):
            return value
        assert isinstance(value, dict)

        self.instance = make_mdl(self.model_container, value)
        return self.instance

    def formfield(self, **kwargs):
        defaults = {
            'form_class': EmbeddedFormField,
            'model_container': self.model_container,
            'model_form_class': self.model_form_class,
            'model_form_kw': self.model_form_kwargs,
            'name': self.attname
        }

        defaults.update(kwargs)
        return super().formfield(**defaults)


class EmbeddedFormField(forms.MultiValueField):
    def __init__(self, name, model_form_class, model_form_kw, model_container,
                 admin=None, request=None, *args, **kwargs):
        form_fields = []
        mdl_form_field_names = []
        widgets = []
        model_form_kwargs = model_form_kw.copy()

        try:
            model_form_kwargs['prefix'] = model_form_kwargs['prefix'] + '-' + name
        except KeyError:
            model_form_kwargs['prefix'] = name

        initial = kwargs.pop('initial', None)
        if initial:
            model_form_kwargs['initial'] = initial

        self.model_form_class = _get_model_form_class(
            model_form_class, model_container, admin, request)
        self.model_form_kwargs = model_form_kwargs
        self.admin = admin
        self.request = request

        error_messages = {
            'incomplete': 'Enter all required fields.',
        }

        self.model_form = self.model_form_class(**model_form_kwargs)
        for field_name, field in self.model_form.fields.items():
            if isinstance(field, (forms.ModelChoiceField, forms.ModelMultipleChoiceField)):
                continue
            form_fields.append(field)
            mdl_form_field_names.append(field_name)
            widgets.append(field.widget)

        widget = EmbeddedFormWidget(mdl_form_field_names, widgets)
        super().__init__(error_messages=error_messages, fields=form_fields,
                         widget=widget, require_all_fields=False, *args, **kwargs)

    def compress(self, clean_data_vals):
        model_field = dict(zip(self.model_form.fields.keys(), clean_data_vals))
        return self.model_form._meta.model(**model_field)

    def get_bound_field(self, form, field_name):
        if form.prefix:
            self.model_form.prefix = '{}-{}'.format(form.prefix, self.model_form.prefix)
        return EmbeddedFormBoundField(form, self, field_name)

    def bound_data(self, data, initial):
        if self.disabled:
            return initial
        return self.compress(data)


class EmbeddedFormBoundField(forms.BoundField):
    # def __getitem__(self, name):
    #     return self.field.model_form[name]
    #
    # def __getattr__(self, name):
    #     return getattr(self.field.model_form, name)

    def __str__(self):
        instance = self.value()
        model_form = self.field.model_form_class(instance=instance, **self.field.model_form_kwargs)

        return mark_safe(f'<table>\n{ model_form.as_table() }\n</table>')


class EmbeddedFormWidget(forms.MultiWidget):
    def __init__(self, field_names, *args, **kwargs):
        self.field_names = field_names
        super().__init__(*args, **kwargs)

    def decompress(self, value):
        if value is None:
            return []
        elif isinstance(value, list):
            return value
        elif isinstance(value, Model):
            return [getattr(value, f_n) for f_n in self.field_names]
        else:
            raise forms.ValidationError('Expected model-form')

    def value_from_datadict(self, data, files, name):
        ret = []
        for i, wid in enumerate(self.widgets):
            f_n = '{}-{}'.format(name, self.field_names[i])
            ret.append(wid.value_from_datadict(
                data, files, f_n
            ))
        return ret

    def value_omitted_from_data(self, data, files, name):
        return all(
            widget.value_omitted_from_data(
                data, files, '{}-{}'.format(name, self.field_names[i])
            )
            for i, widget in enumerate(self.widgets)
        )

class ObjectIdField(AutoField):
    """
    For every document inserted into a collection MongoDB internally creates an field.
    The field can be referenced from within the Model as _id.
    """

    def __init__(self, *args, **kwargs):
        id_field_args = {
            'primary_key': True,
        }
        id_field_args.update(kwargs)
        super().__init__(*args, **id_field_args)

    def get_prep_value(self, value):
        value = super(AutoField, self).get_prep_value(value)
        if value is None:
            return None
        return value

    def get_db_prep_value(self, value, connection, prepared=False):
        return self.to_python(value)

    def to_python(self, value):
        if isinstance(value, str):
            return ObjectId(value)
        return value


def create_reverse_array_reference_manager(superclass, rel):
    pass

def create_forward_array_reference_manager(superclass, rel):

    if issubclass(superclass, DjongoManager):
        baseclass = superclass
    else:
        baseclass = type('baseclass', (DjongoManager, superclass), {})

    class ArrayReferenceManager(baseclass):

        def __init__(self, instance):
            super().__init__()

            self.instance = instance
            self.model = rel.model
            self.field = rel.field
            self.instance_manager = DjongoManager()
            self.instance_manager.model = instance
            name = self.field.related_fields[0][1].attname
            ids = getattr(instance, self.field.attname) or []

            self.core_filters = {f'{name}__in': ids}

        def add(self, *objs):

            fks = getattr(self.instance, self.field.attname)
            if fks is None:
                fks = set()
                setattr(self.instance, self.field.attname, fks)

            new_fks = set()
            for obj in objs:
                for lh_field, rh_field in self.field.related_fields:
                    new_fks.add(getattr(obj, rh_field.attname))
            fks.update(new_fks)

            remote_field = self.field.remote_field
            db = router.db_for_write(self.instance.__class__, instance=self.instance)
            self.instance_manager.db_manager(db).mongo_update(
                {self.instance._meta.pk.name: self.instance.pk},
                {
                    '$addToSet': {
                        self.field.attname: {
                            '$each': list(new_fks)
                        }
                    }
                }
            )


        def remove(self, *objs):
            pass

        def clear(self):
            pass

    return ArrayReferenceManager

class ReverseArrayReferenceDescriptor(ReverseManyToOneDescriptor):

    @cached_property
    def related_manager_cls(self):
        related_model = self.rel.related_model

        return create_reverse_array_reference_manager(
            related_model._default_manager.__class__,
            self.rel,
        )

class ArrayReferenceDescriptor(ForwardManyToOneDescriptor):

    @cached_property
    def related_manager_cls(self):
        related_model = self.field.related_model

        return create_forward_array_reference_manager(
            related_model._default_manager.__class__,
            self.field.remote_field,
        )

    def __get__(self, instance, cls=None):
        """
        Get the related objects through the reverse relation.

        With the example above, when getting ``parent.children``:

        - ``self`` is the descriptor managing the ``children`` attribute
        - ``instance`` is the ``parent`` instance
        - ``cls`` is the ``Parent`` class (unused)
        """
        if instance is None:
            return self

        return self.related_manager_cls(instance)

# class ArrayManyToManyField(ManyToManyField):
#
#     def contribute_to_class(self, cls, name, **kwargs):
#         super().contribute_to_class(cls, name, **kwargs)
#         setattr(cls, self.name, ArrayManyToManyDescriptor(self.remote_field, reverse=False))


class ArrayReferenceField(ForeignKey):
    """
    When the entry gets saved, only a reference to the primary_key of the model is saved in the array.
    For all practical aspects, the ArrayReferenceField behaves like a Django ManyToManyField.
    """

    many_to_many = False
    many_to_one = True
    one_to_many = False
    one_to_one = False
    # rel_class = ManyToManyRel
    related_accessor_class = ReverseArrayReferenceDescriptor
    forward_related_accessor_class = ArrayReferenceDescriptor

    def __init__(self, to, on_delete=None, related_name=None, related_query_name=None,
                 limit_choices_to=None, parent_link=False, to_field=None,
                 db_constraint=True, **kwargs):

        on_delete = on_delete or CASCADE
        super().__init__(to, on_delete=on_delete, related_name=related_name,
                         related_query_name=related_query_name,
                         limit_choices_to=limit_choices_to,
                         parent_link=parent_link, to_field=to_field,
                         db_constraint=db_constraint, **kwargs)

        self.concrete = False

    # def contribute_to_class(self, cls, name, private_only=False, **kwargs):
    #     super().contribute_to_class(cls, name, private_only, **kwargs)
    #     cls._meta.local_fields.remove(self)

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is None:
            return []
        return value
        # return super().get_db_prep_value(value, connection, prepared)

    def get_db_prep_save(self, value, connection):
        if value is None:
            return []
        return list(value)


class GenericReferenceField(FieldCacheMixin):
    pass
