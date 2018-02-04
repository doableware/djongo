"""
The standard way of using djongo is to import models.py
in place of Django's standard models module.
"""
from django.db.models import *
from django import forms
from django.core.exceptions import ValidationError
from django.db import connection
import typing

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
        try:
            return super().__getattr__(name)

        except AttributeError:
            if not name.startswith('mongo_'):
                raise AttributeError
            name = name.strip('mongo_')
            m_cli = connection.cursor().db_conn[self.model._meta.db_table]
            return getattr(m_cli, name)


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

    def get_db_prep_value(self, value, connection, prepared):
        if prepared:
            return value

        if not isinstance(value, list):
            raise TypeError('Object must be of type list')

        ret = []
        for a_mdl in value:
            mdl_ob = {}
            if not isinstance(a_mdl, Model):
                raise TypeError('Array items must be of type Model')
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


class ArrayFormField(forms.Field):
    def __init__(self, name, model_form_class, mdl_form_kw_l, *args, **kwargs):
        self.name = name
        self.model_form_class = model_form_class
        self.mdl_form_kw_l = mdl_form_kw_l

        widget = ArrayFormWidget(model_form_class._meta.fields[0])
        error_messages = {
            'incomplete': 'Enter all required fields.',
        }

        self.ArrayFormSet = forms.formset_factory(self.model_form_class, can_delete=True)
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
        ArrayFormSet = forms.formset_factory(field.model_form_class, can_delete=True)

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

        self.form_set = ArrayFormSet(data, initial=initial,
                                     prefix=name)

    def __getitem__(self, idx):
        if not isinstance(idx, (int, slice)):
            raise TypeError
        return self.form_set[idx]

    def __iter__(self):
        for form in self.form_set:
            yield form

    def __str__(self):
        return mark_safe(f'<table>\n{str(self.form_set)}\n</table>')

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
    def __init__(self,
                 model_container: typing.Type[Model],
                 model_form_class: typing.Type[forms.ModelForm]=None,
                 model_form_kwargs: dict=None,
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
        if not self.model_form_class:
            raise ValidationError('Implementing model form class needed to create field')

        defaults = {
            'form_class': EmbeddedFormField,
            'model_form_class': self.model_form_class,
            'model_form_kw': self.model_form_kwargs,
            'name': self.attname
        }

        defaults.update(kwargs)
        return super().formfield(**defaults)


class EmbeddedFormField(forms.MultiValueField):
    def __init__(self, name, model_form_class, model_form_kw, *args, **kwargs):
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

        self.model_form_class = model_form_class
        self.model_form_kwargs = model_form_kwargs

        error_messages = {
            'incomplete': 'Enter all required fields.',
        }

        self.model_form = model_form_class(**model_form_kwargs)
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


class ReferenceField(ForeignKey):
    pass