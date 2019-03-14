import unittest

from django.conf import settings
from django.core.checks import Error
from django.core.checks.model_checks import _check_lazy_references
from django.core.exceptions import ImproperlyConfigured
from django.db import connections, models
from django.db.models.signals import post_init
from django.test import SimpleTestCase
from django.test.utils import isolate_apps, override_settings


def get_max_column_name_length():
    allowed_len = None
    db_alias = None

    for db in settings.DATABASES:
        connection = connections[db]
        max_name_length = connection.ops.max_name_length()
        if max_name_length is not None and not connection.features.truncates_names:
            if allowed_len is None or max_name_length < allowed_len:
                allowed_len = max_name_length
                db_alias = db

    return (allowed_len, db_alias)


@isolate_apps('invalid_models_tests')
class IndexTogetherTests(SimpleTestCase):

    def test_non_iterable(self):
        class Model(models.Model):
            class Meta:
                index_together = 42

        self.assertEqual(Model.check(), [
            Error(
                "'index_together' must be a list or tuple.",
                obj=Model,
                id='models.E008',
            ),
        ])

    def test_non_list(self):
        class Model(models.Model):
            class Meta:
                index_together = 'not-a-list'

        self.assertEqual(Model.check(), [
            Error(
                "'index_together' must be a list or tuple.",
                obj=Model,
                id='models.E008',
            ),
        ])

    def test_list_containing_non_iterable(self):
        class Model(models.Model):
            class Meta:
                index_together = [('a', 'b'), 42]

        self.assertEqual(Model.check(), [
            Error(
                "All 'index_together' elements must be lists or tuples.",
                obj=Model,
                id='models.E009',
            ),
        ])

    def test_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                index_together = [['missing_field']]

        self.assertEqual(Model.check(), [
            Error(
                "'index_together' refers to the nonexistent field 'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ])

    def test_pointing_to_non_local_field(self):
        class Foo(models.Model):
            field1 = models.IntegerField()

        class Bar(Foo):
            field2 = models.IntegerField()

            class Meta:
                index_together = [['field2', 'field1']]

        self.assertEqual(Bar.check(), [
            Error(
                "'index_together' refers to field 'field1' which is not "
                "local to model 'Bar'.",
                hint='This issue may be caused by multi-table inheritance.',
                obj=Bar,
                id='models.E016',
            ),
        ])

    def test_pointing_to_m2m_field(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                index_together = [['m2m']]

        self.assertEqual(Model.check(), [
            Error(
                "'index_together' refers to a ManyToManyField 'm2m', but "
                "ManyToManyFields are not permitted in 'index_together'.",
                obj=Model,
                id='models.E013',
            ),
        ])


# unique_together tests are very similar to index_together tests.
@isolate_apps('invalid_models_tests')
class UniqueTogetherTests(SimpleTestCase):

    def test_non_iterable(self):
        class Model(models.Model):
            class Meta:
                unique_together = 42

        self.assertEqual(Model.check(), [
            Error(
                "'unique_together' must be a list or tuple.",
                obj=Model,
                id='models.E010',
            ),
        ])

    def test_list_containing_non_iterable(self):
        class Model(models.Model):
            one = models.IntegerField()
            two = models.IntegerField()

            class Meta:
                unique_together = [('a', 'b'), 42]

        self.assertEqual(Model.check(), [
            Error(
                "All 'unique_together' elements must be lists or tuples.",
                obj=Model,
                id='models.E011',
            ),
        ])

    def test_non_list(self):
        class Model(models.Model):
            class Meta:
                unique_together = 'not-a-list'

        self.assertEqual(Model.check(), [
            Error(
                "'unique_together' must be a list or tuple.",
                obj=Model,
                id='models.E010',
            ),
        ])

    def test_valid_model(self):
        class Model(models.Model):
            one = models.IntegerField()
            two = models.IntegerField()

            class Meta:
                # unique_together can be a simple tuple
                unique_together = ('one', 'two')

        self.assertEqual(Model.check(), [])

    def test_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                unique_together = [['missing_field']]

        self.assertEqual(Model.check(), [
            Error(
                "'unique_together' refers to the nonexistent field 'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ])

    def test_pointing_to_m2m(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                unique_together = [['m2m']]

        self.assertEqual(Model.check(), [
            Error(
                "'unique_together' refers to a ManyToManyField 'm2m', but "
                "ManyToManyFields are not permitted in 'unique_together'.",
                obj=Model,
                id='models.E013',
            ),
        ])


@isolate_apps('invalid_models_tests')
class IndexesTests(SimpleTestCase):

    def test_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                indexes = [models.Index(fields=['missing_field'], name='name')]

        self.assertEqual(Model.check(), [
            Error(
                "'indexes' refers to the nonexistent field 'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ])

    def test_pointing_to_m2m_field(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                indexes = [models.Index(fields=['m2m'], name='name')]

        self.assertEqual(Model.check(), [
            Error(
                "'indexes' refers to a ManyToManyField 'm2m', but "
                "ManyToManyFields are not permitted in 'indexes'.",
                obj=Model,
                id='models.E013',
            ),
        ])

    def test_pointing_to_non_local_field(self):
        class Foo(models.Model):
            field1 = models.IntegerField()

        class Bar(Foo):
            field2 = models.IntegerField()

            class Meta:
                indexes = [models.Index(fields=['field2', 'field1'], name='name')]

        self.assertEqual(Bar.check(), [
            Error(
                "'indexes' refers to field 'field1' which is not local to "
                "model 'Bar'.",
                hint='This issue may be caused by multi-table inheritance.',
                obj=Bar,
                id='models.E016',
            ),
        ])


@isolate_apps('invalid_models_tests')
class FieldNamesTests(SimpleTestCase):

    def test_ending_with_underscore(self):
        class Model(models.Model):
            field_ = models.CharField(max_length=10)
            m2m_ = models.ManyToManyField('self')

        self.assertEqual(Model.check(), [
            Error(
                'Field names must not end with an underscore.',
                obj=Model._meta.get_field('field_'),
                id='fields.E001',
            ),
            Error(
                'Field names must not end with an underscore.',
                obj=Model._meta.get_field('m2m_'),
                id='fields.E001',
            ),
        ])

    max_column_name_length, column_limit_db_alias = get_max_column_name_length()

    @unittest.skipIf(max_column_name_length is None, "The database doesn't have a column name length limit.")
    def test_M2M_long_column_name(self):
        """
        #13711 -- Model check for long M2M column names when database has
        column name length limits.
        """
        allowed_len, db_alias = get_max_column_name_length()

        # A model with very long name which will be used to set relations to.
        class VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz(models.Model):
            title = models.CharField(max_length=11)

        # Main model for which checks will be performed.
        class ModelWithLongField(models.Model):
            m2m_field = models.ManyToManyField(
                VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                related_name='rn1',
            )
            m2m_field2 = models.ManyToManyField(
                VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                related_name='rn2', through='m2msimple',
            )
            m2m_field3 = models.ManyToManyField(
                VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                related_name='rn3',
                through='m2mcomplex',
            )
            fk = models.ForeignKey(
                VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                models.CASCADE,
                related_name='rn4',
            )

        # Models used for setting `through` in M2M field.
        class m2msimple(models.Model):
            id2 = models.ForeignKey(ModelWithLongField, models.CASCADE)

        class m2mcomplex(models.Model):
            id2 = models.ForeignKey(ModelWithLongField, models.CASCADE)

        long_field_name = 'a' * (self.max_column_name_length + 1)
        models.ForeignKey(
            VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
            models.CASCADE,
        ).contribute_to_class(m2msimple, long_field_name)

        models.ForeignKey(
            VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
            models.CASCADE,
            db_column=long_field_name
        ).contribute_to_class(m2mcomplex, long_field_name)

        errors = ModelWithLongField.check()

        # First error because of M2M field set on the model with long name.
        m2m_long_name = "verylongmodelnamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz_id"
        if self.max_column_name_length > len(m2m_long_name):
            # Some databases support names longer than the test name.
            expected = []
        else:
            expected = [
                Error(
                    'Autogenerated column name too long for M2M field "%s". '
                    'Maximum length is "%s" for database "%s".'
                    % (m2m_long_name, self.max_column_name_length, self.column_limit_db_alias),
                    hint="Use 'through' to create a separate model for "
                         "M2M and then set column_name using 'db_column'.",
                    obj=ModelWithLongField,
                    id='models.E019',
                )
            ]

        # Second error because the FK specified in the `through` model
        # `m2msimple` has auto-generated name longer than allowed.
        # There will be no check errors in the other M2M because it
        # specifies db_column for the FK in `through` model even if the actual
        # name is longer than the limits of the database.
        expected.append(
            Error(
                'Autogenerated column name too long for M2M field "%s_id". '
                'Maximum length is "%s" for database "%s".'
                % (long_field_name, self.max_column_name_length, self.column_limit_db_alias),
                hint="Use 'through' to create a separate model for "
                     "M2M and then set column_name using 'db_column'.",
                obj=ModelWithLongField,
                id='models.E019',
            )
        )

        self.assertEqual(errors, expected)

    @unittest.skipIf(max_column_name_length is None, "The database doesn't have a column name length limit.")
    def test_local_field_long_column_name(self):
        """
        #13711 -- Model check for long column names
        when database does not support long names.
        """
        allowed_len, db_alias = get_max_column_name_length()

        class ModelWithLongField(models.Model):
            title = models.CharField(max_length=11)

        long_field_name = 'a' * (self.max_column_name_length + 1)
        long_field_name2 = 'b' * (self.max_column_name_length + 1)
        models.CharField(max_length=11).contribute_to_class(ModelWithLongField, long_field_name)
        models.CharField(max_length=11, db_column='vlmn').contribute_to_class(ModelWithLongField, long_field_name2)
        self.assertEqual(ModelWithLongField.check(), [
            Error(
                'Autogenerated column name too long for field "%s". '
                'Maximum length is "%s" for database "%s".'
                % (long_field_name, self.max_column_name_length, self.column_limit_db_alias),
                hint="Set the column name manually using 'db_column'.",
                obj=ModelWithLongField,
                id='models.E018',
            )
        ])

    def test_including_separator(self):
        class Model(models.Model):
            some__field = models.IntegerField()

        self.assertEqual(Model.check(), [
            Error(
                'Field names must not contain "__".',
                obj=Model._meta.get_field('some__field'),
                id='fields.E002',
            )
        ])

    def test_pk(self):
        class Model(models.Model):
            pk = models.IntegerField()

        self.assertEqual(Model.check(), [
            Error(
                "'pk' is a reserved word that cannot be used as a field name.",
                obj=Model._meta.get_field('pk'),
                id='fields.E003',
            )
        ])


@isolate_apps('invalid_models_tests')
class ShadowingFieldsTests(SimpleTestCase):

    def test_field_name_clash_with_child_accessor(self):
        class Parent(models.Model):
            pass

        class Child(Parent):
            child = models.CharField(max_length=100)

        self.assertEqual(Child.check(), [
            Error(
                "The field 'child' clashes with the field "
                "'child' from model 'invalid_models_tests.parent'.",
                obj=Child._meta.get_field('child'),
                id='models.E006',
            )
        ])

    def test_multiinheritance_clash(self):
        class Mother(models.Model):
            clash = models.IntegerField()

        class Father(models.Model):
            clash = models.IntegerField()

        class Child(Mother, Father):
            # Here we have two clashed: id (automatic field) and clash, because
            # both parents define these fields.
            pass

        self.assertEqual(Child.check(), [
            Error(
                "The field 'id' from parent model "
                "'invalid_models_tests.mother' clashes with the field 'id' "
                "from parent model 'invalid_models_tests.father'.",
                obj=Child,
                id='models.E005',
            ),
            Error(
                "The field 'clash' from parent model "
                "'invalid_models_tests.mother' clashes with the field 'clash' "
                "from parent model 'invalid_models_tests.father'.",
                obj=Child,
                id='models.E005',
            )
        ])

    def test_inheritance_clash(self):
        class Parent(models.Model):
            f_id = models.IntegerField()

        class Target(models.Model):
            # This field doesn't result in a clash.
            f_id = models.IntegerField()

        class Child(Parent):
            # This field clashes with parent "f_id" field.
            f = models.ForeignKey(Target, models.CASCADE)

        self.assertEqual(Child.check(), [
            Error(
                "The field 'f' clashes with the field 'f_id' "
                "from model 'invalid_models_tests.parent'.",
                obj=Child._meta.get_field('f'),
                id='models.E006',
            )
        ])

    def test_multigeneration_inheritance(self):
        class GrandParent(models.Model):
            clash = models.IntegerField()

        class Parent(GrandParent):
            pass

        class Child(Parent):
            pass

        class GrandChild(Child):
            clash = models.IntegerField()

        self.assertEqual(GrandChild.check(), [
            Error(
                "The field 'clash' clashes with the field 'clash' "
                "from model 'invalid_models_tests.grandparent'.",
                obj=GrandChild._meta.get_field('clash'),
                id='models.E006',
            )
        ])

    def test_id_clash(self):
        class Target(models.Model):
            pass

        class Model(models.Model):
            fk = models.ForeignKey(Target, models.CASCADE)
            fk_id = models.IntegerField()

        self.assertEqual(Model.check(), [
            Error(
                "The field 'fk_id' clashes with the field 'fk' from model "
                "'invalid_models_tests.model'.",
                obj=Model._meta.get_field('fk_id'),
                id='models.E006',
            )
        ])


@isolate_apps('invalid_models_tests')
class OtherModelTests(SimpleTestCase):

    def test_unique_primary_key(self):
        invalid_id = models.IntegerField(primary_key=False)

        class Model(models.Model):
            id = invalid_id

        self.assertEqual(Model.check(), [
            Error(
                "'id' can only be used as a field name if the field also sets "
                "'primary_key=True'.",
                obj=Model,
                id='models.E004',
            ),
        ])

    def test_ordering_non_iterable(self):
        class Model(models.Model):
            class Meta:
                ordering = 'missing_field'

        self.assertEqual(Model.check(), [
            Error(
                "'ordering' must be a tuple or list "
                "(even if you want to order by only one field).",
                obj=Model,
                id='models.E014',
            ),
        ])

    def test_just_ordering_no_errors(self):
        class Model(models.Model):
            order = models.PositiveIntegerField()

            class Meta:
                ordering = ['order']

        self.assertEqual(Model.check(), [])

    def test_just_order_with_respect_to_no_errors(self):
        class Question(models.Model):
            pass

        class Answer(models.Model):
            question = models.ForeignKey(Question, models.CASCADE)

            class Meta:
                order_with_respect_to = 'question'

        self.assertEqual(Answer.check(), [])

    def test_ordering_with_order_with_respect_to(self):
        class Question(models.Model):
            pass

        class Answer(models.Model):
            question = models.ForeignKey(Question, models.CASCADE)
            order = models.IntegerField()

            class Meta:
                order_with_respect_to = 'question'
                ordering = ['order']

        self.assertEqual(Answer.check(), [
            Error(
                "'ordering' and 'order_with_respect_to' cannot be used together.",
                obj=Answer,
                id='models.E021',
            ),
        ])

    def test_non_valid(self):
        class RelationModel(models.Model):
            pass

        class Model(models.Model):
            relation = models.ManyToManyField(RelationModel)

            class Meta:
                ordering = ['relation']

        self.assertEqual(Model.check(), [
            Error(
                "'ordering' refers to the nonexistent field 'relation'.",
                obj=Model,
                id='models.E015',
            ),
        ])

    def test_ordering_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                ordering = ('missing_field',)

        self.assertEqual(Model.check(), [
            Error(
                "'ordering' refers to the nonexistent field 'missing_field'.",
                obj=Model,
                id='models.E015',
            )
        ])

    def test_ordering_pointing_to_missing_foreignkey_field(self):
        class Model(models.Model):
            missing_fk_field = models.IntegerField()

            class Meta:
                ordering = ('missing_fk_field_id',)

        self.assertEqual(Model.check(), [
            Error(
                "'ordering' refers to the nonexistent field 'missing_fk_field_id'.",
                obj=Model,
                id='models.E015',
            )
        ])

    def test_ordering_pointing_to_foreignkey_field(self):
        class Parent(models.Model):
            pass

        class Child(models.Model):
            parent = models.ForeignKey(Parent, models.CASCADE)

            class Meta:
                ordering = ('parent_id',)

        self.assertFalse(Child.check())

    def test_name_beginning_with_underscore(self):
        class _Model(models.Model):
            pass

        self.assertEqual(_Model.check(), [
            Error(
                "The model name '_Model' cannot start or end with an underscore "
                "as it collides with the query lookup syntax.",
                obj=_Model,
                id='models.E023',
            )
        ])

    def test_name_ending_with_underscore(self):
        class Model_(models.Model):
            pass

        self.assertEqual(Model_.check(), [
            Error(
                "The model name 'Model_' cannot start or end with an underscore "
                "as it collides with the query lookup syntax.",
                obj=Model_,
                id='models.E023',
            )
        ])

    def test_name_contains_double_underscores(self):
        class Test__Model(models.Model):
            pass

        self.assertEqual(Test__Model.check(), [
            Error(
                "The model name 'Test__Model' cannot contain double underscores "
                "as it collides with the query lookup syntax.",
                obj=Test__Model,
                id='models.E024',
            )
        ])

    def test_property_and_related_field_accessor_clash(self):
        class Model(models.Model):
            fk = models.ForeignKey('self', models.CASCADE)

            @property
            def fk_id(self):
                pass

        self.assertEqual(Model.check(), [
            Error(
                "The property 'fk_id' clashes with a related field accessor.",
                obj=Model,
                id='models.E025',
            )
        ])

    def test_single_primary_key(self):
        class Model(models.Model):
            foo = models.IntegerField(primary_key=True)
            bar = models.IntegerField(primary_key=True)

        self.assertEqual(Model.check(), [
            Error(
                "The model cannot have more than one field with 'primary_key=True'.",
                obj=Model,
                id='models.E026',
            )
        ])

    @override_settings(TEST_SWAPPED_MODEL_BAD_VALUE='not-a-model')
    def test_swappable_missing_app_name(self):
        class Model(models.Model):
            class Meta:
                swappable = 'TEST_SWAPPED_MODEL_BAD_VALUE'

        self.assertEqual(Model.check(), [
            Error(
                "'TEST_SWAPPED_MODEL_BAD_VALUE' is not of the form 'app_label.app_name'.",
                id='models.E001',
            ),
        ])

    @override_settings(TEST_SWAPPED_MODEL_BAD_MODEL='not_an_app.Target')
    def test_swappable_missing_app(self):
        class Model(models.Model):
            class Meta:
                swappable = 'TEST_SWAPPED_MODEL_BAD_MODEL'

        self.assertEqual(Model.check(), [
            Error(
                "'TEST_SWAPPED_MODEL_BAD_MODEL' references 'not_an_app.Target', "
                'which has not been installed, or is abstract.',
                id='models.E002',
            ),
        ])

    def test_two_m2m_through_same_relationship(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            primary = models.ManyToManyField(Person, through='Membership', related_name='primary')
            secondary = models.ManyToManyField(Person, through='Membership', related_name='secondary')

        class Membership(models.Model):
            person = models.ForeignKey(Person, models.CASCADE)
            group = models.ForeignKey(Group, models.CASCADE)

        self.assertEqual(Group.check(), [
            Error(
                "The model has two many-to-many relations through "
                "the intermediate model 'invalid_models_tests.Membership'.",
                obj=Group,
                id='models.E003',
            )
        ])

    def test_missing_parent_link(self):
        msg = 'Add parent_link=True to invalid_models_tests.ParkingLot.parent.'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            class Place(models.Model):
                pass

            class ParkingLot(Place):
                parent = models.OneToOneField(Place, models.CASCADE)

    def test_m2m_table_name_clash(self):
        class Foo(models.Model):
            bar = models.ManyToManyField('Bar', db_table='myapp_bar')

            class Meta:
                db_table = 'myapp_foo'

        class Bar(models.Model):
            class Meta:
                db_table = 'myapp_bar'

        self.assertEqual(Foo.check(), [
            Error(
                "The field's intermediary table 'myapp_bar' clashes with the "
                "table name of 'invalid_models_tests.Bar'.",
                obj=Foo._meta.get_field('bar'),
                id='fields.E340',
            )
        ])

    def test_m2m_field_table_name_clash(self):
        class Foo(models.Model):
            pass

        class Bar(models.Model):
            foos = models.ManyToManyField(Foo, db_table='clash')

        class Baz(models.Model):
            foos = models.ManyToManyField(Foo, db_table='clash')

        self.assertEqual(Bar.check() + Baz.check(), [
            Error(
                "The field's intermediary table 'clash' clashes with the "
                "table name of 'invalid_models_tests.Baz.foos'.",
                obj=Bar._meta.get_field('foos'),
                id='fields.E340',
            ),
            Error(
                "The field's intermediary table 'clash' clashes with the "
                "table name of 'invalid_models_tests.Bar.foos'.",
                obj=Baz._meta.get_field('foos'),
                id='fields.E340',
            )
        ])

    def test_m2m_autogenerated_table_name_clash(self):
        class Foo(models.Model):
            class Meta:
                db_table = 'bar_foos'

        class Bar(models.Model):
            # The autogenerated `db_table` will be bar_foos.
            foos = models.ManyToManyField(Foo)

            class Meta:
                db_table = 'bar'

        self.assertEqual(Bar.check(), [
            Error(
                "The field's intermediary table 'bar_foos' clashes with the "
                "table name of 'invalid_models_tests.Foo'.",
                obj=Bar._meta.get_field('foos'),
                id='fields.E340',
            )
        ])

    def test_m2m_unmanaged_shadow_models_not_checked(self):
        class A1(models.Model):
            pass

        class C1(models.Model):
            mm_a = models.ManyToManyField(A1, db_table='d1')

        # Unmanaged models that shadow the above models. Reused table names
        # shouldn't be flagged by any checks.
        class A2(models.Model):
            class Meta:
                managed = False

        class C2(models.Model):
            mm_a = models.ManyToManyField(A2, through='Intermediate')

            class Meta:
                managed = False

        class Intermediate(models.Model):
            a2 = models.ForeignKey(A2, models.CASCADE, db_column='a1_id')
            c2 = models.ForeignKey(C2, models.CASCADE, db_column='c1_id')

            class Meta:
                db_table = 'd1'
                managed = False

        self.assertEqual(C1.check(), [])
        self.assertEqual(C2.check(), [])

    def test_m2m_to_concrete_and_proxy_allowed(self):
        class A(models.Model):
            pass

        class Through(models.Model):
            a = models.ForeignKey('A', models.CASCADE)
            c = models.ForeignKey('C', models.CASCADE)

        class ThroughProxy(Through):
            class Meta:
                proxy = True

        class C(models.Model):
            mm_a = models.ManyToManyField(A, through=Through)
            mm_aproxy = models.ManyToManyField(A, through=ThroughProxy, related_name='proxied_m2m')

        self.assertEqual(C.check(), [])

    @isolate_apps('django.contrib.auth', kwarg_name='apps')
    def test_lazy_reference_checks(self, apps):
        class DummyModel(models.Model):
            author = models.ForeignKey('Author', models.CASCADE)

            class Meta:
                app_label = 'invalid_models_tests'

        class DummyClass:
            def __call__(self, **kwargs):
                pass

            def dummy_method(self):
                pass

        def dummy_function(*args, **kwargs):
            pass

        apps.lazy_model_operation(dummy_function, ('auth', 'imaginarymodel'))
        apps.lazy_model_operation(dummy_function, ('fanciful_app', 'imaginarymodel'))

        post_init.connect(dummy_function, sender='missing-app.Model', apps=apps)
        post_init.connect(DummyClass(), sender='missing-app.Model', apps=apps)
        post_init.connect(DummyClass().dummy_method, sender='missing-app.Model', apps=apps)

        self.assertEqual(_check_lazy_references(apps), [
            Error(
                "%r contains a lazy reference to auth.imaginarymodel, "
                "but app 'auth' doesn't provide model 'imaginarymodel'." % dummy_function,
                obj=dummy_function,
                id='models.E022',
            ),
            Error(
                "%r contains a lazy reference to fanciful_app.imaginarymodel, "
                "but app 'fanciful_app' isn't installed." % dummy_function,
                obj=dummy_function,
                id='models.E022',
            ),
            Error(
                "An instance of class 'DummyClass' was connected to "
                "the 'post_init' signal with a lazy reference to the sender "
                "'missing-app.model', but app 'missing-app' isn't installed.",
                hint=None,
                obj='invalid_models_tests.test_models',
                id='signals.E001',
            ),
            Error(
                "Bound method 'DummyClass.dummy_method' was connected to the "
                "'post_init' signal with a lazy reference to the sender "
                "'missing-app.model', but app 'missing-app' isn't installed.",
                hint=None,
                obj='invalid_models_tests.test_models',
                id='signals.E001',
            ),
            Error(
                "The field invalid_models_tests.DummyModel.author was declared "
                "with a lazy reference to 'invalid_models_tests.author', but app "
                "'invalid_models_tests' isn't installed.",
                hint=None,
                obj=DummyModel.author.field,
                id='fields.E307',
            ),
            Error(
                "The function 'dummy_function' was connected to the 'post_init' "
                "signal with a lazy reference to the sender "
                "'missing-app.model', but app 'missing-app' isn't installed.",
                hint=None,
                obj='invalid_models_tests.test_models',
                id='signals.E001',
            ),
        ])
