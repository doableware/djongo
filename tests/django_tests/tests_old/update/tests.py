from django.core.exceptions import FieldError
from django.db.models import Count, F, Max
from django.test import TestCase

from .models import A, B, Bar, D, DataPoint, Foo, RelatedPoint


class SimpleTest(TestCase):
    def setUp(self):
        self.a1 = A.objects.create()
        self.a2 = A.objects.create()
        for x in range(20):
            B.objects.create(a=self.a1)
            D.objects.create(a=self.a1)

    def test_nonempty_update(self):
        """
        Update changes the right number of rows for a nonempty queryset
        """
        num_updated = self.a1.b_set.update(y=100)
        self.assertEqual(num_updated, 20)
        cnt = B.objects.filter(y=100).count()
        self.assertEqual(cnt, 20)

    def test_empty_update(self):
        """
        Update changes the right number of rows for an empty queryset
        """
        num_updated = self.a2.b_set.update(y=100)
        self.assertEqual(num_updated, 0)
        cnt = B.objects.filter(y=100).count()
        self.assertEqual(cnt, 0)

    def test_nonempty_update_with_inheritance(self):
        """
        Update changes the right number of rows for an empty queryset
        when the update affects only a base table
        """
        num_updated = self.a1.d_set.update(y=100)
        self.assertEqual(num_updated, 20)
        cnt = D.objects.filter(y=100).count()
        self.assertEqual(cnt, 20)

    def test_empty_update_with_inheritance(self):
        """
        Update changes the right number of rows for an empty queryset
        when the update affects only a base table
        """
        num_updated = self.a2.d_set.update(y=100)
        self.assertEqual(num_updated, 0)
        cnt = D.objects.filter(y=100).count()
        self.assertEqual(cnt, 0)

    def test_foreign_key_update_with_id(self):
        """
        Update works using <field>_id for foreign keys
        """
        num_updated = self.a1.d_set.update(a_id=self.a2)
        self.assertEqual(num_updated, 20)
        self.assertEqual(self.a2.d_set.count(), 20)


class AdvancedTests(TestCase):

    def setUp(self):
        self.d0 = DataPoint.objects.create(name="d0", value="apple")
        self.d2 = DataPoint.objects.create(name="d2", value="banana")
        self.d3 = DataPoint.objects.create(name="d3", value="banana")
        self.r1 = RelatedPoint.objects.create(name="r1", data=self.d3)

    def test_update(self):
        """
        Objects are updated by first filtering the candidates into a queryset
        and then calling the update() method. It executes immediately and
        returns nothing.
        """
        resp = DataPoint.objects.filter(value="apple").update(name="d1")
        self.assertEqual(resp, 1)
        resp = DataPoint.objects.filter(value="apple")
        self.assertEqual(list(resp), [self.d0])

    def test_update_multiple_objects(self):
        """
        We can update multiple objects at once.
        """
        resp = DataPoint.objects.filter(value="banana").update(
            value="pineapple")
        self.assertEqual(resp, 2)
        self.assertEqual(DataPoint.objects.get(name="d2").value, 'pineapple')

    def test_update_fk(self):
        """
        Foreign key fields can also be updated, although you can only update
        the object referred to, not anything inside the related object.
        """
        resp = RelatedPoint.objects.filter(name="r1").update(data=self.d0)
        self.assertEqual(resp, 1)
        resp = RelatedPoint.objects.filter(data__name="d0")
        self.assertEqual(list(resp), [self.r1])

    def test_update_multiple_fields(self):
        """
        Multiple fields can be updated at once
        """
        resp = DataPoint.objects.filter(value="apple").update(
            value="fruit", another_value="peach")
        self.assertEqual(resp, 1)
        d = DataPoint.objects.get(name="d0")
        self.assertEqual(d.value, 'fruit')
        self.assertEqual(d.another_value, 'peach')

    def test_update_all(self):
        """
        In the rare case you want to update every instance of a model, update()
        is also a manager method.
        """
        self.assertEqual(DataPoint.objects.update(value='thing'), 3)
        resp = DataPoint.objects.values('value').distinct()
        self.assertEqual(list(resp), [{'value': 'thing'}])

    def test_update_slice_fail(self):
        """
        We do not support update on already sliced query sets.
        """
        method = DataPoint.objects.all()[:2].update
        msg = 'Cannot update a query once a slice has been taken.'
        with self.assertRaisesMessage(AssertionError, msg):
            method(another_value='another thing')

    def test_update_respects_to_field(self):
        """
        Update of an FK field which specifies a to_field works.
        """
        a_foo = Foo.objects.create(target='aaa')
        b_foo = Foo.objects.create(target='bbb')
        bar = Bar.objects.create(foo=a_foo)
        self.assertEqual(bar.foo_id, a_foo.target)
        bar_qs = Bar.objects.filter(pk=bar.pk)
        self.assertEqual(bar_qs[0].foo_id, a_foo.target)
        bar_qs.update(foo=b_foo)
        self.assertEqual(bar_qs[0].foo_id, b_foo.target)

    def test_update_m2m_field(self):
        msg = (
            'Cannot update model field '
            '<django.db.models.fields.related.ManyToManyField: m2m_foo> '
            '(only non-relations and foreign keys permitted).'
        )
        with self.assertRaisesMessage(FieldError, msg):
            Bar.objects.update(m2m_foo='whatever')

    def test_update_annotated_queryset(self):
        """
        Update of a queryset that's been annotated.
        """
        # Trivial annotated update
        qs = DataPoint.objects.annotate(alias=F('value'))
        self.assertEqual(qs.update(another_value='foo'), 3)
        # Update where annotation is used for filtering
        qs = DataPoint.objects.annotate(alias=F('value')).filter(alias='apple')
        self.assertEqual(qs.update(another_value='foo'), 1)
        # Update where annotation is used in update parameters
        qs = DataPoint.objects.annotate(alias=F('value'))
        self.assertEqual(qs.update(another_value=F('alias')), 3)
        # Update where aggregation annotation is used in update parameters
        qs = DataPoint.objects.annotate(max=Max('value'))
        with self.assertRaisesMessage(FieldError, 'Aggregate functions are not allowed in this query'):
            qs.update(another_value=F('max'))

    def test_update_annotated_multi_table_queryset(self):
        """
        Update of a queryset that's been annotated and involves multiple tables.
        """
        # Trivial annotated update
        qs = DataPoint.objects.annotate(related_count=Count('relatedpoint'))
        self.assertEqual(qs.update(value='Foo'), 3)
        # Update where annotation is used for filtering
        qs = DataPoint.objects.annotate(related_count=Count('relatedpoint'))
        self.assertEqual(qs.filter(related_count=1).update(value='Foo'), 1)
        # Update where annotation is used in update parameters
        # #26539 - This isn't forbidden but also doesn't generate proper SQL
        # qs = RelatedPoint.objects.annotate(data_name=F('data__name'))
        # updated = qs.update(name=F('data_name'))
        # self.assertEqual(updated, 1)
        # Update where aggregation annotation is used in update parameters
        qs = RelatedPoint.objects.annotate(max=Max('data__value'))
        with self.assertRaisesMessage(FieldError, 'Aggregate functions are not allowed in this query'):
            qs.update(name=F('max'))
