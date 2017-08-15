from django.db.models import *
from django import forms
from django.core.exceptions import ValidationError
from django.db import connection


def make_mdl(mdl, mdl_dict):
    for field_name in mdl_dict:
        field = mdl._meta.get_field(field_name)
        mdl_dict[field_name] = field.to_python(mdl_dict[field_name])
    return mdl(**mdl_dict)


def useful_field(field):
    return field.concrete and not (field.is_relation \
                                   or isinstance(field, (AutoField, BigAutoField)))


class DjongoManager(Manager):
    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError:
            if not name.startswith('mongo_'):
                raise AttributeError
            name = name.strip('mongo_')
            m_cli = connection.cursor().m_cli_connection[self.model._meta.db_table]
            return getattr(m_cli, name)


class ArrayModelField(Field):
    def __init__(self, model_container, model_form=None,
                 model_form_kwargs_l={}, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_container = model_container
        self.model_form = model_form
        self.model_form_kwargs_l = model_form_kwargs_l

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['model_container'] = self.model_container
        if self.model_form is not None:
            kwargs['model_form'] = self.model_form
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
        defaults = {
            'form_class': ArrayFormField,
            'mdl_form': self.model_form,
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
    def __init__(self, name, mdl_form, mdl_form_kw_l, *args, **kwargs):
        self.name = name
        self.mdl_form = mdl_form
        self.mdl_form_kw_l = mdl_form_kw_l

        widget = ArrayFormWidget(mdl_form._meta.fields[0])
        error_messages = {
            'incomplete': 'Enter all required fields.',
        }

        self.ArrayFormSet = forms.formset_factory(self.mdl_form, can_delete=True)
        super().__init__(error_messages=error_messages,
                         widget=widget, *args, **kwargs)

    def clean(self, value):
        if not value:
            return []
        form_set = self.ArrayFormSet(value, prefix=self.name)
        if form_set.is_valid():
            ret = []
            for itm in form_set.cleaned_data:
                if itm.get('DELETE', False):
                    continue
                itm.pop('DELETE')
                ret.append(self.mdl_form._meta.model(**itm))
            return ret
        else:
            raise ValidationError(form_set.errors + form_set.non_form_errors())

    def has_changed(self, initial, data):
        form_set = self.ArrayFormSet(data, initial=initial, prefix=self.name)
        return form_set.has_changed()

    def get_bound_field(self, form, field_name):
        return ArrayFormBoundField(form, self, field_name)


class ArrayFormBoundField(forms.BoundField):
    def __init__(self, form, field, name):
        super().__init__(form, field, name)
        ArrayFormSet = forms.formset_factory(field.mdl_form, can_delete=True)

        data = self.data if form.is_bound else None
        initial = []
        if self.initial is not None:
            for ini in self.initial:
                if isinstance(ini, Model):
                    initial.append(
                        forms.model_to_dict(
                            ini,
                            fields=field.mdl_form._meta.fields,
                            exclude=field.mdl_form._meta.exclude
                        ))
        self.form_set = ArrayFormSet(data, initial=initial,
                                     prefix=name)

    def __getitem__(self, idx):
        if not isinstance(idx, int):
            raise TypeError
        return self.form_set[idx]

    def __iter__(self):
        for form in self.form_set:
            yield form

    def __str__(self):
        return '<table>\n{}\n</table>'.format(str(self.form_set))

    def __len__(self):
        return len(self.form_set)


class ArrayFormWidget(forms.Widget):
    def __init__(self, first_field_id, attrs=None):
        self.first_field_id = first_field_id
        super().__init__(attrs)

    def render(self, name, value, attrs=None):
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
    def __init__(self, model_container,
                 model_form=None, model_form_kwargs={},
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_container = model_container
        self.model_form = model_form
        self.model_form_kwargs = model_form_kwargs

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['model_container'] = self.model_container
        if self.model_form is not None:
            kwargs['model_form'] = self.model_form
        return name, path, args, kwargs

    def get_db_prep_value(self, value):
        if not isinstance(value, Model):
            raise TypeError('Object must be of type Model')
        mdl_ob = {}
        for fld in value._meta.get_fields():
            if not useful_field(fld):
                continue
            fld_value = getattr(a_mdl, fld.attname)
            mdl_ob[fld.attname] = fld.get_db_prep_value(fld_value)
        return mdl_ob

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        if value is None or isinstance(value, self.model_container):
            return value
        assert isinstance(value, dict)
        return make_mdl(self.model_container, value)

    def formfield(self, **kwargs):
        if not self.model_form:
            raise ValidationError('Implementing model form class needed to create field')
        defaults = {
            'form_class': EmbeddedFormField,
            'mdl_form': self.model_form,
            'mdl_form_kw': self.model_form_kwargs,
            'name': self.attname
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class EmbeddedFormField(forms.MultiValueField):
    def __init__(self, name, mdl_form, mdl_form_kw, *args, **kwargs):
        form_fields = []
        mdl_form_field_names = []
        widgets = []
        try:
            mdl_form_kw['prefix'] = '{}-{}'.format(mdl_form_kw['prefix'], name)
        except KeyError:
            mdl_form_kw['prefix'] = name
        mdl_form = mdl_form(**mdl_form_kw)
        self.mdl_form = mdl_form

        error_messages = {
            'incomplete': 'Enter all required fields.',
        }
        for fld_name, fld in mdl_form.fields.items():
            if isinstance(fld, (forms.ModelChoiceField, forms.ModelMultipleChoiceField)):
                continue
            form_fields.append(fld)
            mdl_form_field_names.append(fld_name)
            widgets.append(fld.widget)

        widget = EmbeddedFormWidget(mdl_form_field_names, widgets)
        super().__init__(error_messages=error_messages, fields=form_fields,
                         widget=widget, require_all_fields=False, *args, **kwargs)

    def compress(self, clean_data_vals):
        mdl_fi = dict(zip(self.mdl_form.fields.keys(), clean_data_vals))
        return self.mdl_form.model(**mdl_fi)

    def get_bound_field(self, form, field_name):
        if form.prefix:
            self.mdl_form.prefix = '{}-{}'.format(form.prefix, self.mdl_form.prefix)
        return EmbeddedFormBoundField(form, self, field_name)


class EmbeddedFormBoundField(forms.BoundField):
    def __getitem__(self, name):
        return self.field.mdl_form[name]

    def __getattr__(self, name):
        return getattr(self.field.mdl_form, name)

    def __str__(self):
        return self.field.mdl_form.as_table()


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
            return [getattr(f_n, value) for f_n in self.field_names]
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
