import datetime

from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.templatetags.admin_list import pagination
from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.admin.views.main import (
    ALL_VAR, IS_POPUP_VAR, ORDER_VAR, PAGE_VAR, SEARCH_VAR, TO_FIELD_VAR,
)
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.storage.cookie import CookieStorage
from django.db import connection, models
from django.db.models import F, Field, IntegerField
from django.db.models.functions import Upper
from django.db.models.lookups import Contains, Exact
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.test.utils import (
    CaptureQueriesContext, isolate_apps, register_lookup,
)
from django.urls import reverse
from django.utils import formats

from .admin import (
    BandAdmin, ChildAdmin, ChordsBandAdmin, ConcertAdmin,
    CustomPaginationAdmin, CustomPaginator, DynamicListDisplayChildAdmin,
    DynamicListDisplayLinksChildAdmin, DynamicListFilterChildAdmin,
    DynamicSearchFieldsChildAdmin, EmptyValueChildAdmin, EventAdmin,
    FilteredChildAdmin, GroupAdmin, InvitationAdmin,
    NoListDisplayLinksParentAdmin, ParentAdmin, QuartetAdmin, SwallowAdmin,
    site as custom_site,
)
from .models import (
    Band, CharPK, Child, ChordsBand, ChordsMusician, Concert, CustomIdUser,
    Event, Genre, Group, Invitation, Membership, Musician, OrderedObject,
    Parent, Quartet, Swallow, SwallowOneToOne, UnorderedObject,
)


def build_tbody_html(pk, href, extra_fields):
    return (
        '<tbody><tr>'
        '<td class="action-checkbox">'
        '<input type="checkbox" name="_selected_action" value="{}" '
        'class="action-select"></td>'
        '<th class="field-name"><a href="{}">name</a></th>'
        '{}</tr></tbody>'
    ).format(pk, href, extra_fields)


@override_settings(ROOT_URLCONF="admin_changelist.urls")
class ChangeListTests(TestCase):
    factory = RequestFactory()

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(username='super', email='a@b.com', password='xxx')

    def _create_superuser(self, username):
        return User.objects.create_superuser(username=username, email='a@b.com', password='xxx')

    def _mocked_authenticated_request(self, url, user):
        request = self.factory.get(url)
        request.user = user
        return request

    def test_specified_ordering_by_f_expression(self):
        class OrderedByFBandAdmin(admin.ModelAdmin):
            list_display = ['name', 'genres', 'nr_of_members']
            ordering = (
                F('nr_of_members').desc(nulls_last=True),
                Upper(F('name')).asc(),
                F('genres').asc(),
            )

        m = OrderedByFBandAdmin(Band, custom_site)
        request = self.factory.get('/band/')
        request.user = self.superuser
        cl = m.get_changelist_instance(request)
        self.assertEqual(cl.get_ordering_field_columns(), {3: 'desc', 2: 'asc'})

    def test_specified_ordering_by_f_expression_without_asc_desc(self):
        class OrderedByFBandAdmin(admin.ModelAdmin):
            list_display = ['name', 'genres', 'nr_of_members']
            ordering = (F('nr_of_members'), Upper('name'), F('genres'))

        m = OrderedByFBandAdmin(Band, custom_site)
        request = self.factory.get('/band/')
        request.user = self.superuser
        cl = m.get_changelist_instance(request)
        self.assertEqual(cl.get_ordering_field_columns(), {3: 'asc', 2: 'asc'})

    def test_select_related_preserved(self):
        """
        Regression test for #10348: ChangeList.get_queryset() shouldn't
        overwrite a custom select_related provided by ModelAdmin.get_queryset().
        """
        m = ChildAdmin(Child, custom_site)
        request = self.factory.get('/child/')
        request.user = self.superuser
        cl = m.get_changelist_instance(request)
        self.assertEqual(cl.queryset.query.select_related, {'parent': {}})

    def test_select_related_as_tuple(self):
        ia = InvitationAdmin(Invitation, custom_site)
        request = self.factory.get('/invitation/')
        request.user = self.superuser
        cl = ia.get_changelist_instance(request)
        self.assertEqual(cl.queryset.query.select_related, {'player': {}})

    def test_select_related_as_empty_tuple(self):
        ia = InvitationAdmin(Invitation, custom_site)
        ia.list_select_related = ()
        request = self.factory.get('/invitation/')
        request.user = self.superuser
        cl = ia.get_changelist_instance(request)
        self.assertIs(cl.queryset.query.select_related, False)

    def test_get_select_related_custom_method(self):
        class GetListSelectRelatedAdmin(admin.ModelAdmin):
            list_display = ('band', 'player')

            def get_list_select_related(self, request):
                return ('band', 'player')

        ia = GetListSelectRelatedAdmin(Invitation, custom_site)
        request = self.factory.get('/invitation/')
        request.user = self.superuser
        cl = ia.get_changelist_instance(request)
        self.assertEqual(cl.queryset.query.select_related, {'player': {}, 'band': {}})

    def test_result_list_empty_changelist_value(self):
        """
        Regression test for #14982: EMPTY_CHANGELIST_VALUE should be honored
        for relationship fields
        """
        new_child = Child.objects.create(name='name', parent=None)
        request = self.factory.get('/child/')
        request.user = self.superuser
        m = ChildAdmin(Child, custom_site)
        cl = m.get_changelist_instance(request)
        cl.formset = None
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl, 'opts': Child._meta})
        table_output = template.render(context)
        link = reverse('admin:admin_changelist_child_change', args=(new_child.id,))
        row_html = build_tbody_html(new_child.id, link, '<td class="field-parent nowrap">-</td>')
        self.assertNotEqual(table_output.find(row_html), -1, 'Failed to find expected row element: %s' % table_output)

    def test_result_list_set_empty_value_display_on_admin_site(self):
        """
        Empty value display can be set on AdminSite.
        """
        new_child = Child.objects.create(name='name', parent=None)
        request = self.factory.get('/child/')
        request.user = self.superuser
        # Set a new empty display value on AdminSite.
        admin.site.empty_value_display = '???'
        m = ChildAdmin(Child, admin.site)
        cl = m.get_changelist_instance(request)
        cl.formset = None
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl, 'opts': Child._meta})
        table_output = template.render(context)
        link = reverse('admin:admin_changelist_child_change', args=(new_child.id,))
        row_html = build_tbody_html(new_child.id, link, '<td class="field-parent nowrap">???</td>')
        self.assertNotEqual(table_output.find(row_html), -1, 'Failed to find expected row element: %s' % table_output)

    def test_result_list_set_empty_value_display_in_model_admin(self):
        """
        Empty value display can be set in ModelAdmin or individual fields.
        """
        new_child = Child.objects.create(name='name', parent=None)
        request = self.factory.get('/child/')
        request.user = self.superuser
        m = EmptyValueChildAdmin(Child, admin.site)
        cl = m.get_changelist_instance(request)
        cl.formset = None
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl, 'opts': Child._meta})
        table_output = template.render(context)
        link = reverse('admin:admin_changelist_child_change', args=(new_child.id,))
        row_html = build_tbody_html(
            new_child.id,
            link,
            '<td class="field-age_display">&amp;dagger;</td>'
            '<td class="field-age">-empty-</td>'
        )
        self.assertNotEqual(table_output.find(row_html), -1, 'Failed to find expected row element: %s' % table_output)

    def test_result_list_html(self):
        """
        Inclusion tag result_list generates a table when with default
        ModelAdmin settings.
        """
        new_parent = Parent.objects.create(name='parent')
        new_child = Child.objects.create(name='name', parent=new_parent)
        request = self.factory.get('/child/')
        request.user = self.superuser
        m = ChildAdmin(Child, custom_site)
        cl = m.get_changelist_instance(request)
        cl.formset = None
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl, 'opts': Child._meta})
        table_output = template.render(context)
        link = reverse('admin:admin_changelist_child_change', args=(new_child.id,))
        row_html = build_tbody_html(new_child.id, link, '<td class="field-parent nowrap">%s</td>' % new_parent)
        self.assertNotEqual(table_output.find(row_html), -1, 'Failed to find expected row element: %s' % table_output)

    def test_result_list_editable_html(self):
        """
        Regression tests for #11791: Inclusion tag result_list generates a
        table and this checks that the items are nested within the table
        element tags.
        Also a regression test for #13599, verifies that hidden fields
        when list_editable is enabled are rendered in a div outside the
        table.
        """
        new_parent = Parent.objects.create(name='parent')
        new_child = Child.objects.create(name='name', parent=new_parent)
        request = self.factory.get('/child/')
        request.user = self.superuser
        m = ChildAdmin(Child, custom_site)

        # Test with list_editable fields
        m.list_display = ['id', 'name', 'parent']
        m.list_display_links = ['id']
        m.list_editable = ['name']
        cl = m.get_changelist_instance(request)
        FormSet = m.get_changelist_formset(request)
        cl.formset = FormSet(queryset=cl.result_list)
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl, 'opts': Child._meta})
        table_output = template.render(context)
        # make sure that hidden fields are in the correct place
        hiddenfields_div = (
            '<div class="hiddenfields">'
            '<input type="hidden" name="form-0-id" value="%d" id="id_form-0-id">'
            '</div>'
        ) % new_child.id
        self.assertInHTML(hiddenfields_div, table_output, msg_prefix='Failed to find hidden fields')

        # make sure that list editable fields are rendered in divs correctly
        editable_name_field = (
            '<input name="form-0-name" value="name" class="vTextField" '
            'maxlength="30" type="text" id="id_form-0-name">'
        )
        self.assertInHTML(
            '<td class="field-name">%s</td>' % editable_name_field,
            table_output,
            msg_prefix='Failed to find "name" list_editable field',
        )

    def test_result_list_editable(self):
        """
        Regression test for #14312: list_editable with pagination
        """
        new_parent = Parent.objects.create(name='parent')
        for i in range(1, 201):
            Child.objects.create(name='name %s' % i, parent=new_parent)
        request = self.factory.get('/child/', data={'p': -1})  # Anything outside range
        request.user = self.superuser
        m = ChildAdmin(Child, custom_site)

        # Test with list_editable fields
        m.list_display = ['id', 'name', 'parent']
        m.list_display_links = ['id']
        m.list_editable = ['name']
        with self.assertRaises(IncorrectLookupParameters):
            m.get_changelist_instance(request)

    def test_custom_paginator(self):
        new_parent = Parent.objects.create(name='parent')
        for i in range(1, 201):
            Child.objects.create(name='name %s' % i, parent=new_parent)

        request = self.factory.get('/child/')
        request.user = self.superuser
        m = CustomPaginationAdmin(Child, custom_site)

        cl = m.get_changelist_instance(request)
        cl.get_results(request)
        self.assertIsInstance(cl.paginator, CustomPaginator)

    def test_no_duplicates_for_m2m_in_list_filter(self):
        """
        Regression test for #13902: When using a ManyToMany in list_filter,
        results shouldn't appear more than once. Basic ManyToMany.
        """
        blues = Genre.objects.create(name='Blues')
        band = Band.objects.create(name='B.B. King Review', nr_of_members=11)

        band.genres.add(blues)
        band.genres.add(blues)

        m = BandAdmin(Band, custom_site)
        request = self.factory.get('/band/', data={'genres': blues.pk})
        request.user = self.superuser

        cl = m.get_changelist_instance(request)
        cl.get_results(request)

        # There's only one Group instance
        self.assertEqual(cl.result_count, 1)
        # Queryset must be deletable.
        self.assertIs(cl.queryset.query.distinct, False)
        cl.queryset.delete()
        self.assertEqual(cl.queryset.count(), 0)

    def test_no_duplicates_for_through_m2m_in_list_filter(self):
        """
        Regression test for #13902: When using a ManyToMany in list_filter,
        results shouldn't appear more than once. With an intermediate model.
        """
        lead = Musician.objects.create(name='Vox')
        band = Group.objects.create(name='The Hype')
        Membership.objects.create(group=band, music=lead, role='lead voice')
        Membership.objects.create(group=band, music=lead, role='bass player')

        m = GroupAdmin(Group, custom_site)
        request = self.factory.get('/group/', data={'members': lead.pk})
        request.user = self.superuser

        cl = m.get_changelist_instance(request)
        cl.get_results(request)

        # There's only one Group instance
        self.assertEqual(cl.result_count, 1)
        # Queryset must be deletable.
        self.assertIs(cl.queryset.query.distinct, False)
        cl.queryset.delete()
        self.assertEqual(cl.queryset.count(), 0)

    def test_no_duplicates_for_through_m2m_at_second_level_in_list_filter(self):
        """
        When using a ManyToMany in list_filter at the second level behind a
        ForeignKey, results shouldn't appear more than once.
        """
        lead = Musician.objects.create(name='Vox')
        band = Group.objects.create(name='The Hype')
        Concert.objects.create(name='Woodstock', group=band)
        Membership.objects.create(group=band, music=lead, role='lead voice')
        Membership.objects.create(group=band, music=lead, role='bass player')

        m = ConcertAdmin(Concert, custom_site)
        request = self.factory.get('/concert/', data={'group__members': lead.pk})
        request.user = self.superuser

        cl = m.get_changelist_instance(request)
        cl.get_results(request)

        # There's only one Concert instance
        self.assertEqual(cl.result_count, 1)
        # Queryset must be deletable.
        self.assertIs(cl.queryset.query.distinct, False)
        cl.queryset.delete()
        self.assertEqual(cl.queryset.count(), 0)

    def test_no_duplicates_for_inherited_m2m_in_list_filter(self):
        """
        Regression test for #13902: When using a ManyToMany in list_filter,
        results shouldn't appear more than once. Model managed in the
        admin inherits from the one that defines the relationship.
        """
        lead = Musician.objects.create(name='John')
        four = Quartet.objects.create(name='The Beatles')
        Membership.objects.create(group=four, music=lead, role='lead voice')
        Membership.objects.create(group=four, music=lead, role='guitar player')

        m = QuartetAdmin(Quartet, custom_site)
        request = self.factory.get('/quartet/', data={'members': lead.pk})
        request.user = self.superuser

        cl = m.get_changelist_instance(request)
        cl.get_results(request)

        # There's only one Quartet instance
        self.assertEqual(cl.result_count, 1)
        # Queryset must be deletable.
        self.assertIs(cl.queryset.query.distinct, False)
        cl.queryset.delete()
        self.assertEqual(cl.queryset.count(), 0)

    def test_no_duplicates_for_m2m_to_inherited_in_list_filter(self):
        """
        Regression test for #13902: When using a ManyToMany in list_filter,
        results shouldn't appear more than once. Target of the relationship
        inherits from another.
        """
        lead = ChordsMusician.objects.create(name='Player A')
        three = ChordsBand.objects.create(name='The Chords Trio')
        Invitation.objects.create(band=three, player=lead, instrument='guitar')
        Invitation.objects.create(band=three, player=lead, instrument='bass')

        m = ChordsBandAdmin(ChordsBand, custom_site)
        request = self.factory.get('/chordsband/', data={'members': lead.pk})
        request.user = self.superuser

        cl = m.get_changelist_instance(request)
        cl.get_results(request)

        # There's only one ChordsBand instance
        self.assertEqual(cl.result_count, 1)
        # Queryset must be deletable.
        self.assertIs(cl.queryset.query.distinct, False)
        cl.queryset.delete()
        self.assertEqual(cl.queryset.count(), 0)

    def test_no_duplicates_for_non_unique_related_object_in_list_filter(self):
        """
        Regressions tests for #15819: If a field listed in list_filters is a
        non-unique related object, results shouldn't appear more than once.
        """
        parent = Parent.objects.create(name='Mary')
        # Two children with the same name
        Child.objects.create(parent=parent, name='Daniel')
        Child.objects.create(parent=parent, name='Daniel')

        m = ParentAdmin(Parent, custom_site)
        request = self.factory.get('/parent/', data={'child__name': 'Daniel'})
        request.user = self.superuser

        cl = m.get_changelist_instance(request)
        # Exists() is applied.
        self.assertEqual(cl.queryset.count(), 1)
        # Queryset must be deletable.
        self.assertIs(cl.queryset.query.distinct, False)
        cl.queryset.delete()
        self.assertEqual(cl.queryset.count(), 0)

    def test_changelist_search_form_validation(self):
        m = ConcertAdmin(Concert, custom_site)
        tests = [
            ({SEARCH_VAR: '\x00'}, 'Null characters are not allowed.'),
            ({SEARCH_VAR: 'some\x00thing'}, 'Null characters are not allowed.'),
        ]
        for case, error in tests:
            with self.subTest(case=case):
                request = self.factory.get('/concert/', case)
                request.user = self.superuser
                request._messages = CookieStorage(request)
                m.get_changelist_instance(request)
                messages = [m.message for m in request._messages]
                self.assertEqual(1, len(messages))
                self.assertEqual(error, messages[0])

    def test_no_duplicates_for_non_unique_related_object_in_search_fields(self):
        """
        Regressions tests for #15819: If a field listed in search_fields
        is a non-unique related object, Exists() must be applied.
        """
        parent = Parent.objects.create(name='Mary')
        Child.objects.create(parent=parent, name='Danielle')
        Child.objects.create(parent=parent, name='Daniel')

        m = ParentAdmin(Parent, custom_site)
        request = self.factory.get('/parent/', data={SEARCH_VAR: 'daniel'})
        request.user = self.superuser

        cl = m.get_changelist_instance(request)
        # Exists() is applied.
        self.assertEqual(cl.queryset.count(), 1)
        # Queryset must be deletable.
        self.assertIs(cl.queryset.query.distinct, False)
        cl.queryset.delete()
        self.assertEqual(cl.queryset.count(), 0)

    def test_no_duplicates_for_many_to_many_at_second_level_in_search_fields(self):
        """
        When using a ManyToMany in search_fields at the second level behind a
        ForeignKey, Exists() must be applied and results shouldn't appear more
        than once.
        """
        lead = Musician.objects.create(name='Vox')
        band = Group.objects.create(name='The Hype')
        Concert.objects.create(name='Woodstock', group=band)
        Membership.objects.create(group=band, music=lead, role='lead voice')
        Membership.objects.create(group=band, music=lead, role='bass player')

        m = ConcertAdmin(Concert, custom_site)
        request = self.factory.get('/concert/', data={SEARCH_VAR: 'vox'})
        request.user = self.superuser

        cl = m.get_changelist_instance(request)
        # There's only one Concert instance
        self.assertEqual(cl.queryset.count(), 1)
        # Queryset must be deletable.
        self.assertIs(cl.queryset.query.distinct, False)
        cl.queryset.delete()
        self.assertEqual(cl.queryset.count(), 0)

    def test_pk_in_search_fields(self):
        band = Group.objects.create(name='The Hype')
        Concert.objects.create(name='Woodstock', group=band)

        m = ConcertAdmin(Concert, custom_site)
        m.search_fields = ['group__pk']

        request = self.factory.get('/concert/', data={SEARCH_VAR: band.pk})
        request.user = self.superuser
        cl = m.get_changelist_instance(request)
        self.assertEqual(cl.queryset.count(), 1)

        request = self.factory.get('/concert/', data={SEARCH_VAR: band.pk + 5})
        request.user = self.superuser
        cl = m.get_changelist_instance(request)
        self.assertEqual(cl.queryset.count(), 0)

    def test_builtin_lookup_in_search_fields(self):
        band = Group.objects.create(name='The Hype')
        concert = Concert.objects.create(name='Woodstock', group=band)

        m = ConcertAdmin(Concert, custom_site)
        m.search_fields = ['name__iexact']

        request = self.factory.get('/', data={SEARCH_VAR: 'woodstock'})
        request.user = self.superuser
        cl = m.get_changelist_instance(request)
        self.assertCountEqual(cl.queryset, [concert])

        request = self.factory.get('/', data={SEARCH_VAR: 'wood'})
        request.user = self.superuser
        cl = m.get_changelist_instance(request)
        self.assertCountEqual(cl.queryset, [])

    def test_custom_lookup_in_search_fields(self):
        band = Group.objects.create(name='The Hype')
        concert = Concert.objects.create(name='Woodstock', group=band)

        m = ConcertAdmin(Concert, custom_site)
        m.search_fields = ['group__name__cc']
        with register_lookup(Field, Contains, lookup_name='cc'):
            request = self.factory.get('/', data={SEARCH_VAR: 'Hype'})
            request.user = self.superuser
            cl = m.get_changelist_instance(request)
            self.assertCountEqual(cl.queryset, [concert])

            request = self.factory.get('/', data={SEARCH_VAR: 'Woodstock'})
            request.user = self.superuser
            cl = m.get_changelist_instance(request)
            self.assertCountEqual(cl.queryset, [])

    def test_spanning_relations_with_custom_lookup_in_search_fields(self):
        hype = Group.objects.create(name='The Hype')
        concert = Concert.objects.create(name='Woodstock', group=hype)
        vox = Musician.objects.create(name='Vox', age=20)
        Membership.objects.create(music=vox, group=hype)
        # Register a custom lookup on IntegerField to ensure that field
        # traversing logic in ModelAdmin.get_search_results() works.
        with register_lookup(IntegerField, Exact, lookup_name='exactly'):
            m = ConcertAdmin(Concert, custom_site)
            m.search_fields = ['group__members__age__exactly']

            request = self.factory.get('/', data={SEARCH_VAR: '20'})
            request.user = self.superuser
            cl = m.get_changelist_instance(request)
            self.assertCountEqual(cl.queryset, [concert])

            request = self.factory.get('/', data={SEARCH_VAR: '21'})
            request.user = self.superuser
            cl = m.get_changelist_instance(request)
            self.assertCountEqual(cl.queryset, [])

    def test_custom_lookup_with_pk_shortcut(self):
        self.assertEqual(CharPK._meta.pk.name, 'char_pk')  # Not equal to 'pk'.
        m = admin.ModelAdmin(CustomIdUser, custom_site)

        abc = CharPK.objects.create(char_pk='abc')
        abcd = CharPK.objects.create(char_pk='abcd')
        m = admin.ModelAdmin(CharPK, custom_site)
        m.search_fields = ['pk__exact']

        request = self.factory.get('/', data={SEARCH_VAR: 'abc'})
        request.user = self.superuser
        cl = m.get_changelist_instance(request)
        self.assertCountEqual(cl.queryset, [abc])

        request = self.factory.get('/', data={SEARCH_VAR: 'abcd'})
        request.user = self.superuser
        cl = m.get_changelist_instance(request)
        self.assertCountEqual(cl.queryset, [abcd])

    def test_no_exists_for_m2m_in_list_filter_without_params(self):
        """
        If a ManyToManyField is in list_filter but isn't in any lookup params,
        the changelist's query shouldn't have Exists().
        """
        m = BandAdmin(Band, custom_site)
        for lookup_params in ({}, {'name': 'test'}):
            request = self.factory.get('/band/', lookup_params)
            request.user = self.superuser
            cl = m.get_changelist_instance(request)
            self.assertNotIn(' EXISTS', str(cl.queryset.query))

        # A ManyToManyField in params does have Exists() applied.
        request = self.factory.get('/band/', {'genres': '0'})
        request.user = self.superuser
        cl = m.get_changelist_instance(request)
        self.assertIn(' EXISTS', str(cl.queryset.query))

    def test_pagination(self):
        """
        Regression tests for #12893: Pagination in admins changelist doesn't
        use queryset set by modeladmin.
        """
        parent = Parent.objects.create(name='anything')
        for i in range(1, 31):
            Child.objects.create(name='name %s' % i, parent=parent)
            Child.objects.create(name='filtered %s' % i, parent=parent)

        request = self.factory.get('/child/')
        request.user = self.superuser

        # Test default queryset
        m = ChildAdmin(Child, custom_site)
        cl = m.get_changelist_instance(request)
        self.assertEqual(cl.queryset.count(), 60)
        self.assertEqual(cl.paginator.count, 60)
        self.assertEqual(list(cl.paginator.page_range), [1, 2, 3, 4, 5, 6])

        # Test custom queryset
        m = FilteredChildAdmin(Child, custom_site)
        cl = m.get_changelist_instance(request)
        self.assertEqual(cl.queryset.count(), 30)
        self.assertEqual(cl.paginator.count, 30)
        self.assertEqual(list(cl.paginator.page_range), [1, 2, 3])

    def test_computed_list_display_localization(self):
        """
        Regression test for #13196: output of functions should be  localized
        in the changelist.
        """
        self.client.force_login(self.superuser)
        event = Event.objects.create(date=datetime.date.today())
        response = self.client.get(reverse('admin:admin_changelist_event_changelist'))
        self.assertContains(response, formats.localize(event.date))
        self.assertNotContains(response, str(event.date))

    def test_dynamic_list_display(self):
        """
        Regression tests for #14206: dynamic list_display support.
        """
        parent = Parent.objects.create(name='parent')
        for i in range(10):
            Child.objects.create(name='child %s' % i, parent=parent)

        user_noparents = self._create_superuser('noparents')
        user_parents = self._create_superuser('parents')

        # Test with user 'noparents'
        m = custom_site._registry[Child]
        request = self._mocked_authenticated_request('/child/', user_noparents)
        response = m.changelist_view(request)
        self.assertNotContains(response, 'Parent object')

        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        self.assertEqual(list_display, ['name', 'age'])
        self.assertEqual(list_display_links, ['name'])

        # Test with user 'parents'
        m = DynamicListDisplayChildAdmin(Child, custom_site)
        request = self._mocked_authenticated_request('/child/', user_parents)
        response = m.changelist_view(request)
        self.assertContains(response, 'Parent object')

        custom_site.unregister(Child)

        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        self.assertEqual(list_display, ('parent', 'name', 'age'))
        self.assertEqual(list_display_links, ['parent'])

        # Test default implementation
        custom_site.register(Child, ChildAdmin)
        m = custom_site._registry[Child]
        request = self._mocked_authenticated_request('/child/', user_noparents)
        response = m.changelist_view(request)
        self.assertContains(response, 'Parent object')

    def test_show_all(self):
        parent = Parent.objects.create(name='anything')
        for i in range(1, 31):
            Child.objects.create(name='name %s' % i, parent=parent)
            Child.objects.create(name='filtered %s' % i, parent=parent)

        # Add "show all" parameter to request
        request = self.factory.get('/child/', data={ALL_VAR: ''})
        request.user = self.superuser

        # Test valid "show all" request (number of total objects is under max)
        m = ChildAdmin(Child, custom_site)
        m.list_max_show_all = 200
        # 200 is the max we'll pass to ChangeList
        cl = m.get_changelist_instance(request)
        cl.get_results(request)
        self.assertEqual(len(cl.result_list), 60)

        # Test invalid "show all" request (number of total objects over max)
        # falls back to paginated pages
        m = ChildAdmin(Child, custom_site)
        m.list_max_show_all = 30
        # 30 is the max we'll pass to ChangeList for this test
        cl = m.get_changelist_instance(request)
        cl.get_results(request)
        self.assertEqual(len(cl.result_list), 10)

    def test_dynamic_list_display_links(self):
        """
        Regression tests for #16257: dynamic list_display_links support.
        """
        parent = Parent.objects.create(name='parent')
        for i in range(1, 10):
            Child.objects.create(id=i, name='child %s' % i, parent=parent, age=i)

        m = DynamicListDisplayLinksChildAdmin(Child, custom_site)
        superuser = self._create_superuser('superuser')
        request = self._mocked_authenticated_request('/child/', superuser)
        response = m.changelist_view(request)
        for i in range(1, 10):
            link = reverse('admin:admin_changelist_child_change', args=(i,))
            self.assertContains(response, '<a href="%s">%s</a>' % (link, i))

        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        self.assertEqual(list_display, ('parent', 'name', 'age'))
        self.assertEqual(list_display_links, ['age'])

    def test_no_list_display_links(self):
        """#15185 -- Allow no links from the 'change list' view grid."""
        p = Parent.objects.create(name='parent')
        m = NoListDisplayLinksParentAdmin(Parent, custom_site)
        superuser = self._create_superuser('superuser')
        request = self._mocked_authenticated_request('/parent/', superuser)
        response = m.changelist_view(request)
        link = reverse('admin:admin_changelist_parent_change', args=(p.pk,))
        self.assertNotContains(response, '<a href="%s">' % link)

    def test_clear_all_filters_link(self):
        self.client.force_login(self.superuser)
        url = reverse('admin:auth_user_changelist')
        response = self.client.get(url)
        self.assertNotContains(response, '&#10006; Clear all filters')
        link = '<a href="%s">&#10006; Clear all filters</a>'
        for data, href in (
            ({'is_staff__exact': '0'}, '?'),
            (
                {'is_staff__exact': '0', 'username__startswith': 'test'},
                '?username__startswith=test',
            ),
            (
                {'is_staff__exact': '0', SEARCH_VAR: 'test'},
                '?%s=test' % SEARCH_VAR,
            ),
            (
                {'is_staff__exact': '0', IS_POPUP_VAR: 'id'},
                '?%s=id' % IS_POPUP_VAR,
            ),
        ):
            with self.subTest(data=data):
                response = self.client.get(url, data=data)
                self.assertContains(response, link % href)

    def test_clear_all_filters_link_callable_filter(self):
        self.client.force_login(self.superuser)
        url = reverse('admin:admin_changelist_band_changelist')
        response = self.client.get(url)
        self.assertNotContains(response, '&#10006; Clear all filters')
        link = '<a href="%s">&#10006; Clear all filters</a>'
        for data, href in (
            ({'nr_of_members_partition': '5'}, '?'),
            (
                {'nr_of_members_partition': 'more', 'name__startswith': 'test'},
                '?name__startswith=test',
            ),
            (
                {'nr_of_members_partition': '5', IS_POPUP_VAR: 'id'},
                '?%s=id' % IS_POPUP_VAR,
            ),
        ):
            with self.subTest(data=data):
                response = self.client.get(url, data=data)
                self.assertContains(response, link % href)

    def test_no_clear_all_filters_link(self):
        self.client.force_login(self.superuser)
        url = reverse('admin:auth_user_changelist')
        link = '>&#10006; Clear all filters</a>'
        for data in (
            {SEARCH_VAR: 'test'},
            {ORDER_VAR: '-1'},
            {TO_FIELD_VAR: 'id'},
            {PAGE_VAR: '1'},
            {IS_POPUP_VAR: '1'},
            {'username__startswith': 'test'},
        ):
            with self.subTest(data=data):
                response = self.client.get(url, data=data)
                self.assertNotContains(response, link)

    def test_tuple_list_display(self):
        swallow = Swallow.objects.create(origin='Africa', load='12.34', speed='22.2')
        swallow2 = Swallow.objects.create(origin='Africa', load='12.34', speed='22.2')
        swallow_o2o = SwallowOneToOne.objects.create(swallow=swallow2)

        model_admin = SwallowAdmin(Swallow, custom_site)
        superuser = self._create_superuser('superuser')
        request = self._mocked_authenticated_request('/swallow/', superuser)
        response = model_admin.changelist_view(request)
        # just want to ensure it doesn't blow up during rendering
        self.assertContains(response, str(swallow.origin))
        self.assertContains(response, str(swallow.load))
        self.assertContains(response, str(swallow.speed))
        # Reverse one-to-one relations should work.
        self.assertContains(response, '<td class="field-swallowonetoone">-</td>')
        self.assertContains(response, '<td class="field-swallowonetoone">%s</td>' % swallow_o2o)

    def test_multiuser_edit(self):
        """
        Simultaneous edits of list_editable fields on the changelist by
        different users must not result in one user's edits creating a new
        object instead of modifying the correct existing object (#11313).
        """
        # To replicate this issue, simulate the following steps:
        # 1. User1 opens an admin changelist with list_editable fields.
        # 2. User2 edits object "Foo" such that it moves to another page in
        #    the pagination order and saves.
        # 3. User1 edits object "Foo" and saves.
        # 4. The edit made by User1 does not get applied to object "Foo" but
        #    instead is used to create a new object (bug).

        # For this test, order the changelist by the 'speed' attribute and
        # display 3 objects per page (SwallowAdmin.list_per_page = 3).

        # Setup the test to reflect the DB state after step 2 where User2 has
        # edited the first swallow object's speed from '4' to '1'.
        a = Swallow.objects.create(origin='Swallow A', load=4, speed=1)
        b = Swallow.objects.create(origin='Swallow B', load=2, speed=2)
        c = Swallow.objects.create(origin='Swallow C', load=5, speed=5)
        d = Swallow.objects.create(origin='Swallow D', load=9, speed=9)

        superuser = self._create_superuser('superuser')
        self.client.force_login(superuser)
        changelist_url = reverse('admin:admin_changelist_swallow_changelist')

        # Send the POST from User1 for step 3. It's still using the changelist
        # ordering from before User2's edits in step 2.
        data = {
            'form-TOTAL_FORMS': '3',
            'form-INITIAL_FORMS': '3',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-uuid': str(d.pk),
            'form-1-uuid': str(c.pk),
            'form-2-uuid': str(a.pk),
            'form-0-load': '9.0',
            'form-0-speed': '9.0',
            'form-1-load': '5.0',
            'form-1-speed': '5.0',
            'form-2-load': '5.0',
            'form-2-speed': '4.0',
            '_save': 'Save',
        }
        response = self.client.post(changelist_url, data, follow=True, extra={'o': '-2'})

        # The object User1 edited in step 3 is displayed on the changelist and
        # has the correct edits applied.
        self.assertContains(response, '1 swallow was changed successfully.')
        self.assertContains(response, a.origin)
        a.refresh_from_db()
        self.assertEqual(a.load, float(data['form-2-load']))
        self.assertEqual(a.speed, float(data['form-2-speed']))
        b.refresh_from_db()
        self.assertEqual(b.load, 2)
        self.assertEqual(b.speed, 2)
        c.refresh_from_db()
        self.assertEqual(c.load, float(data['form-1-load']))
        self.assertEqual(c.speed, float(data['form-1-speed']))
        d.refresh_from_db()
        self.assertEqual(d.load, float(data['form-0-load']))
        self.assertEqual(d.speed, float(data['form-0-speed']))
        # No new swallows were created.
        self.assertEqual(len(Swallow.objects.all()), 4)

    def test_get_edited_object_ids(self):
        a = Swallow.objects.create(origin='Swallow A', load=4, speed=1)
        b = Swallow.objects.create(origin='Swallow B', load=2, speed=2)
        c = Swallow.objects.create(origin='Swallow C', load=5, speed=5)
        superuser = self._create_superuser('superuser')
        self.client.force_login(superuser)
        changelist_url = reverse('admin:admin_changelist_swallow_changelist')
        m = SwallowAdmin(Swallow, custom_site)
        data = {
            'form-TOTAL_FORMS': '3',
            'form-INITIAL_FORMS': '3',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-uuid': str(a.pk),
            'form-1-uuid': str(b.pk),
            'form-2-uuid': str(c.pk),
            'form-0-load': '9.0',
            'form-0-speed': '9.0',
            'form-1-load': '5.0',
            'form-1-speed': '5.0',
            'form-2-load': '5.0',
            'form-2-speed': '4.0',
            '_save': 'Save',
        }
        request = self.factory.post(changelist_url, data=data)
        pks = m._get_edited_object_pks(request, prefix='form')
        self.assertEqual(sorted(pks), sorted([str(a.pk), str(b.pk), str(c.pk)]))

    def test_get_list_editable_queryset(self):
        a = Swallow.objects.create(origin='Swallow A', load=4, speed=1)
        Swallow.objects.create(origin='Swallow B', load=2, speed=2)
        data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '2',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-uuid': str(a.pk),
            'form-0-load': '10',
            '_save': 'Save',
        }
        superuser = self._create_superuser('superuser')
        self.client.force_login(superuser)
        changelist_url = reverse('admin:admin_changelist_swallow_changelist')
        m = SwallowAdmin(Swallow, custom_site)
        request = self.factory.post(changelist_url, data=data)
        queryset = m._get_list_editable_queryset(request, prefix='form')
        self.assertEqual(queryset.count(), 1)
        data['form-0-uuid'] = 'INVALD_PRIMARY_KEY'
        # The unfiltered queryset is returned if there's invalid data.
        request = self.factory.post(changelist_url, data=data)
        queryset = m._get_list_editable_queryset(request, prefix='form')
        self.assertEqual(queryset.count(), 2)

    def test_get_list_editable_queryset_with_regex_chars_in_prefix(self):
        a = Swallow.objects.create(origin='Swallow A', load=4, speed=1)
        Swallow.objects.create(origin='Swallow B', load=2, speed=2)
        data = {
            'form$-TOTAL_FORMS': '2',
            'form$-INITIAL_FORMS': '2',
            'form$-MIN_NUM_FORMS': '0',
            'form$-MAX_NUM_FORMS': '1000',
            'form$-0-uuid': str(a.pk),
            'form$-0-load': '10',
            '_save': 'Save',
        }
        superuser = self._create_superuser('superuser')
        self.client.force_login(superuser)
        changelist_url = reverse('admin:admin_changelist_swallow_changelist')
        m = SwallowAdmin(Swallow, custom_site)
        request = self.factory.post(changelist_url, data=data)
        queryset = m._get_list_editable_queryset(request, prefix='form$')
        self.assertEqual(queryset.count(), 1)

    def test_changelist_view_list_editable_changed_objects_uses_filter(self):
        """list_editable edits use a filtered queryset to limit memory usage."""
        a = Swallow.objects.create(origin='Swallow A', load=4, speed=1)
        Swallow.objects.create(origin='Swallow B', load=2, speed=2)
        data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '2',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-uuid': str(a.pk),
            'form-0-load': '10',
            '_save': 'Save',
        }
        superuser = self._create_superuser('superuser')
        self.client.force_login(superuser)
        changelist_url = reverse('admin:admin_changelist_swallow_changelist')
        with CaptureQueriesContext(connection) as context:
            response = self.client.post(changelist_url, data=data)
            self.assertEqual(response.status_code, 200)
            self.assertIn('WHERE', context.captured_queries[4]['sql'])
            self.assertIn('IN', context.captured_queries[4]['sql'])
            # Check only the first few characters since the UUID may have dashes.
            self.assertIn(str(a.pk)[:8], context.captured_queries[4]['sql'])

    def test_deterministic_order_for_unordered_model(self):
        """
        The primary key is used in the ordering of the changelist's results to
        guarantee a deterministic order, even when the model doesn't have any
        default ordering defined (#17198).
        """
        superuser = self._create_superuser('superuser')

        for counter in range(1, 51):
            UnorderedObject.objects.create(id=counter, bool=True)

        class UnorderedObjectAdmin(admin.ModelAdmin):
            list_per_page = 10

        def check_results_order(ascending=False):
            custom_site.register(UnorderedObject, UnorderedObjectAdmin)
            model_admin = UnorderedObjectAdmin(UnorderedObject, custom_site)
            counter = 0 if ascending else 51
            for page in range(1, 6):
                request = self._mocked_authenticated_request('/unorderedobject/?p=%s' % page, superuser)
                response = model_admin.changelist_view(request)
                for result in response.context_data['cl'].result_list:
                    counter += 1 if ascending else -1
                    self.assertEqual(result.id, counter)
            custom_site.unregister(UnorderedObject)

        # When no order is defined at all, everything is ordered by '-pk'.
        check_results_order()

        # When an order field is defined but multiple records have the same
        # value for that field, make sure everything gets ordered by -pk as well.
        UnorderedObjectAdmin.ordering = ['bool']
        check_results_order()

        # When order fields are defined, including the pk itself, use them.
        UnorderedObjectAdmin.ordering = ['bool', '-pk']
        check_results_order()
        UnorderedObjectAdmin.ordering = ['bool', 'pk']
        check_results_order(ascending=True)
        UnorderedObjectAdmin.ordering = ['-id', 'bool']
        check_results_order()
        UnorderedObjectAdmin.ordering = ['id', 'bool']
        check_results_order(ascending=True)

    def test_deterministic_order_for_model_ordered_by_its_manager(self):
        """
        The primary key is used in the ordering of the changelist's results to
        guarantee a deterministic order, even when the model has a manager that
        defines a default ordering (#17198).
        """
        superuser = self._create_superuser('superuser')

        for counter in range(1, 51):
            OrderedObject.objects.create(id=counter, bool=True, number=counter)

        class OrderedObjectAdmin(admin.ModelAdmin):
            list_per_page = 10

        def check_results_order(ascending=False):
            custom_site.register(OrderedObject, OrderedObjectAdmin)
            model_admin = OrderedObjectAdmin(OrderedObject, custom_site)
            counter = 0 if ascending else 51
            for page in range(1, 6):
                request = self._mocked_authenticated_request('/orderedobject/?p=%s' % page, superuser)
                response = model_admin.changelist_view(request)
                for result in response.context_data['cl'].result_list:
                    counter += 1 if ascending else -1
                    self.assertEqual(result.id, counter)
            custom_site.unregister(OrderedObject)

        # When no order is defined at all, use the model's default ordering (i.e. 'number')
        check_results_order(ascending=True)

        # When an order field is defined but multiple records have the same
        # value for that field, make sure everything gets ordered by -pk as well.
        OrderedObjectAdmin.ordering = ['bool']
        check_results_order()

        # When order fields are defined, including the pk itself, use them.
        OrderedObjectAdmin.ordering = ['bool', '-pk']
        check_results_order()
        OrderedObjectAdmin.ordering = ['bool', 'pk']
        check_results_order(ascending=True)
        OrderedObjectAdmin.ordering = ['-id', 'bool']
        check_results_order()
        OrderedObjectAdmin.ordering = ['id', 'bool']
        check_results_order(ascending=True)

    @isolate_apps('admin_changelist')
    def test_total_ordering_optimization(self):
        class Related(models.Model):
            unique_field = models.BooleanField(unique=True)

            class Meta:
                ordering = ('unique_field',)

        class Model(models.Model):
            unique_field = models.BooleanField(unique=True)
            unique_nullable_field = models.BooleanField(unique=True, null=True)
            related = models.ForeignKey(Related, models.CASCADE)
            other_related = models.ForeignKey(Related, models.CASCADE)
            related_unique = models.OneToOneField(Related, models.CASCADE)
            field = models.BooleanField()
            other_field = models.BooleanField()
            null_field = models.BooleanField(null=True)

            class Meta:
                unique_together = {
                    ('field', 'other_field'),
                    ('field', 'null_field'),
                    ('related', 'other_related_id'),
                }

        class ModelAdmin(admin.ModelAdmin):
            def get_queryset(self, request):
                return Model.objects.none()

        request = self._mocked_authenticated_request('/', self.superuser)
        site = admin.AdminSite(name='admin')
        model_admin = ModelAdmin(Model, site)
        change_list = model_admin.get_changelist_instance(request)
        tests = (
            ([], ['-pk']),
            # Unique non-nullable field.
            (['unique_field'], ['unique_field']),
            (['-unique_field'], ['-unique_field']),
            # Unique nullable field.
            (['unique_nullable_field'], ['unique_nullable_field', '-pk']),
            # Field.
            (['field'], ['field', '-pk']),
            # Related field introspection is not implemented.
            (['related__unique_field'], ['related__unique_field', '-pk']),
            # Related attname unique.
            (['related_unique_id'], ['related_unique_id']),
            # Related ordering introspection is not implemented.
            (['related_unique'], ['related_unique', '-pk']),
            # Composite unique.
            (['field', '-other_field'], ['field', '-other_field']),
            # Composite unique nullable.
            (['-field', 'null_field'], ['-field', 'null_field', '-pk']),
            # Composite unique and nullable.
            (['-field', 'null_field', 'other_field'], ['-field', 'null_field', 'other_field']),
            # Composite unique attnames.
            (['related_id', '-other_related_id'], ['related_id', '-other_related_id']),
            # Composite unique names.
            (['related', '-other_related_id'], ['related', '-other_related_id', '-pk']),
        )
        # F() objects composite unique.
        total_ordering = [F('field'), F('other_field').desc(nulls_last=True)]
        # F() objects composite unique nullable.
        non_total_ordering = [F('field'), F('null_field').desc(nulls_last=True)]
        tests += (
            (total_ordering, total_ordering),
            (non_total_ordering, non_total_ordering + ['-pk']),
        )
        for ordering, expected in tests:
            with self.subTest(ordering=ordering):
                self.assertEqual(change_list._get_deterministic_ordering(ordering), expected)

    @isolate_apps('admin_changelist')
    def test_total_ordering_optimization_meta_constraints(self):
        class Related(models.Model):
            unique_field = models.BooleanField(unique=True)

            class Meta:
                ordering = ('unique_field',)

        class Model(models.Model):
            field_1 = models.BooleanField()
            field_2 = models.BooleanField()
            field_3 = models.BooleanField()
            field_4 = models.BooleanField()
            field_5 = models.BooleanField()
            field_6 = models.BooleanField()
            nullable_1 = models.BooleanField(null=True)
            nullable_2 = models.BooleanField(null=True)
            related_1 = models.ForeignKey(Related, models.CASCADE)
            related_2 = models.ForeignKey(Related, models.CASCADE)
            related_3 = models.ForeignKey(Related, models.CASCADE)
            related_4 = models.ForeignKey(Related, models.CASCADE)

            class Meta:
                constraints = [
                    *[
                        models.UniqueConstraint(fields=fields, name=''.join(fields))
                        for fields in (
                            ['field_1'],
                            ['nullable_1'],
                            ['related_1'],
                            ['related_2_id'],
                            ['field_2', 'field_3'],
                            ['field_2', 'nullable_2'],
                            ['field_2', 'related_3'],
                            ['field_3', 'related_4_id'],
                        )
                    ],
                    models.CheckConstraint(check=models.Q(id__gt=0), name='foo'),
                    models.UniqueConstraint(
                        fields=['field_5'],
                        condition=models.Q(id__gt=10),
                        name='total_ordering_1',
                    ),
                    models.UniqueConstraint(
                        fields=['field_6'],
                        condition=models.Q(),
                        name='total_ordering',
                    ),
                ]

        class ModelAdmin(admin.ModelAdmin):
            def get_queryset(self, request):
                return Model.objects.none()

        request = self._mocked_authenticated_request('/', self.superuser)
        site = admin.AdminSite(name='admin')
        model_admin = ModelAdmin(Model, site)
        change_list = model_admin.get_changelist_instance(request)
        tests = (
            # Unique non-nullable field.
            (['field_1'], ['field_1']),
            # Unique nullable field.
            (['nullable_1'], ['nullable_1', '-pk']),
            # Related attname unique.
            (['related_1_id'], ['related_1_id']),
            (['related_2_id'], ['related_2_id']),
            # Related ordering introspection is not implemented.
            (['related_1'], ['related_1', '-pk']),
            # Composite unique.
            (['-field_2', 'field_3'], ['-field_2', 'field_3']),
            # Composite unique nullable.
            (['field_2', '-nullable_2'], ['field_2', '-nullable_2', '-pk']),
            # Composite unique and nullable.
            (
                ['field_2', '-nullable_2', 'field_3'],
                ['field_2', '-nullable_2', 'field_3'],
            ),
            # Composite field and related field name.
            (['field_2', '-related_3'], ['field_2', '-related_3', '-pk']),
            (['field_3', 'related_4'], ['field_3', 'related_4', '-pk']),
            # Composite field and related field attname.
            (['field_2', 'related_3_id'], ['field_2', 'related_3_id']),
            (['field_3', '-related_4_id'], ['field_3', '-related_4_id']),
            # Partial unique constraint is ignored.
            (['field_5'], ['field_5', '-pk']),
            # Unique constraint with an empty condition.
            (['field_6'], ['field_6']),
        )
        for ordering, expected in tests:
            with self.subTest(ordering=ordering):
                self.assertEqual(change_list._get_deterministic_ordering(ordering), expected)

    def test_dynamic_list_filter(self):
        """
        Regression tests for ticket #17646: dynamic list_filter support.
        """
        parent = Parent.objects.create(name='parent')
        for i in range(10):
            Child.objects.create(name='child %s' % i, parent=parent)

        user_noparents = self._create_superuser('noparents')
        user_parents = self._create_superuser('parents')

        # Test with user 'noparents'
        m = DynamicListFilterChildAdmin(Child, custom_site)
        request = self._mocked_authenticated_request('/child/', user_noparents)
        response = m.changelist_view(request)
        self.assertEqual(response.context_data['cl'].list_filter, ['name', 'age'])

        # Test with user 'parents'
        m = DynamicListFilterChildAdmin(Child, custom_site)
        request = self._mocked_authenticated_request('/child/', user_parents)
        response = m.changelist_view(request)
        self.assertEqual(response.context_data['cl'].list_filter, ('parent', 'name', 'age'))

    def test_dynamic_search_fields(self):
        child = self._create_superuser('child')
        m = DynamicSearchFieldsChildAdmin(Child, custom_site)
        request = self._mocked_authenticated_request('/child/', child)
        response = m.changelist_view(request)
        self.assertEqual(response.context_data['cl'].search_fields, ('name', 'age'))

    def test_pagination_page_range(self):
        """
        Regression tests for ticket #15653: ensure the number of pages
        generated for changelist views are correct.
        """
        # instantiating and setting up ChangeList object
        m = GroupAdmin(Group, custom_site)
        request = self.factory.get('/group/')
        request.user = self.superuser
        cl = m.get_changelist_instance(request)
        cl.list_per_page = 10

        ELLIPSIS = cl.paginator.ELLIPSIS
        for number, pages, expected in [
            (1, 1, []),
            (1, 2, [1, 2]),
            (6, 11, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]),
            (6, 12, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]),
            (6, 13, [1, 2, 3, 4, 5, 6, 7, 8, 9, ELLIPSIS, 12, 13]),
            (7, 12, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]),
            (7, 13, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]),
            (7, 14, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, ELLIPSIS, 13, 14]),
            (8, 13, [1, 2, ELLIPSIS, 5, 6, 7, 8, 9, 10, 11, 12, 13]),
            (8, 14, [1, 2, ELLIPSIS, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]),
            (8, 15, [1, 2, ELLIPSIS, 5, 6, 7, 8, 9, 10, 11, ELLIPSIS, 14, 15]),
        ]:
            with self.subTest(number=number, pages=pages):
                # assuming exactly `pages * cl.list_per_page` objects
                Group.objects.all().delete()
                for i in range(pages * cl.list_per_page):
                    Group.objects.create(name='test band')

                # setting page number and calculating page range
                cl.page_num = number
                cl.get_results(request)
                self.assertEqual(list(pagination(cl)['page_range']), expected)

    def test_object_tools_displayed_no_add_permission(self):
        """
        When ModelAdmin.has_add_permission() returns False, the object-tools
        block is still shown.
        """
        superuser = self._create_superuser('superuser')
        m = EventAdmin(Event, custom_site)
        request = self._mocked_authenticated_request('/event/', superuser)
        self.assertFalse(m.has_add_permission(request))
        response = m.changelist_view(request)
        self.assertIn('<ul class="object-tools">', response.rendered_content)
        # The "Add" button inside the object-tools shouldn't appear.
        self.assertNotIn('Add ', response.rendered_content)


class GetAdminLogTests(TestCase):

    def test_custom_user_pk_not_named_id(self):
        """
        {% get_admin_log %} works if the user model's primary key isn't named
        'id'.
        """
        context = Context({'user': CustomIdUser()})
        template = Template('{% load log %}{% get_admin_log 10 as admin_log for_user user %}')
        # This template tag just logs.
        self.assertEqual(template.render(context), '')

    def test_no_user(self):
        """{% get_admin_log %} works without specifying a user."""
        user = User(username='jondoe', password='secret', email='super@example.com')
        user.save()
        ct = ContentType.objects.get_for_model(User)
        LogEntry.objects.log_action(user.pk, ct.pk, user.pk, repr(user), 1)
        t = Template(
            '{% load log %}'
            '{% get_admin_log 100 as admin_log %}'
            '{% for entry in admin_log %}'
            '{{ entry|safe }}'
            '{% endfor %}'
        )
        self.assertEqual(t.render(Context({})), 'Added “<User: jondoe>”.')

    def test_missing_args(self):
        msg = "'get_admin_log' statements require two arguments"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            Template('{% load log %}{% get_admin_log 10 as %}')

    def test_non_integer_limit(self):
        msg = "First argument to 'get_admin_log' must be an integer"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            Template('{% load log %}{% get_admin_log "10" as admin_log for_user user %}')

    def test_without_as(self):
        msg = "Second argument to 'get_admin_log' must be 'as'"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            Template('{% load log %}{% get_admin_log 10 ad admin_log for_user user %}')

    def test_without_for_user(self):
        msg = "Fourth argument to 'get_admin_log' must be 'for_user'"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            Template('{% load log %}{% get_admin_log 10 as admin_log foruser user %}')


@override_settings(ROOT_URLCONF='admin_changelist.urls')
class SeleniumTests(AdminSeleniumTestCase):

    available_apps = ['admin_changelist'] + AdminSeleniumTestCase.available_apps

    def setUp(self):
        User.objects.create_superuser(username='super', password='secret', email=None)

    def test_add_row_selection(self):
        """
        The status line for selected rows gets updated correctly (#22038).
        """
        self.admin_login(username='super', password='secret')
        self.selenium.get(self.live_server_url + reverse('admin:auth_user_changelist'))

        form_id = '#changelist-form'

        # Test amount of rows in the Changelist
        rows = self.selenium.find_elements_by_css_selector(
            '%s #result_list tbody tr' % form_id
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]

        selection_indicator = self.selenium.find_element_by_css_selector(
            '%s .action-counter' % form_id
        )
        all_selector = self.selenium.find_element_by_id('action-toggle')
        row_selector = self.selenium.find_element_by_css_selector(
            '%s #result_list tbody tr:first-child .action-select' % form_id
        )

        # Test current selection
        self.assertEqual(selection_indicator.text, "0 of 1 selected")
        self.assertIs(all_selector.get_property('checked'), False)
        self.assertEqual(row.get_attribute('class'), '')

        # Select a row and check again
        row_selector.click()
        self.assertEqual(selection_indicator.text, "1 of 1 selected")
        self.assertIs(all_selector.get_property('checked'), True)
        self.assertEqual(row.get_attribute('class'), 'selected')

        # Deselect a row and check again
        row_selector.click()
        self.assertEqual(selection_indicator.text, "0 of 1 selected")
        self.assertIs(all_selector.get_property('checked'), False)
        self.assertEqual(row.get_attribute('class'), '')

    def test_modifier_allows_multiple_section(self):
        """
        Selecting a row and then selecting another row whilst holding shift
        should select all rows in-between.
        """
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys

        Parent.objects.bulk_create([Parent(name='parent%d' % i) for i in range(5)])
        self.admin_login(username='super', password='secret')
        self.selenium.get(self.live_server_url + reverse('admin:admin_changelist_parent_changelist'))
        checkboxes = self.selenium.find_elements_by_css_selector('tr input.action-select')
        self.assertEqual(len(checkboxes), 5)
        for c in checkboxes:
            self.assertIs(c.get_property('checked'), False)
        # Check first row. Hold-shift and check next-to-last row.
        checkboxes[0].click()
        ActionChains(self.selenium).key_down(Keys.SHIFT).click(checkboxes[-2]).key_up(Keys.SHIFT).perform()
        for c in checkboxes[:-2]:
            self.assertIs(c.get_property('checked'), True)
        self.assertIs(checkboxes[-1].get_property('checked'), False)

    def test_select_all_across_pages(self):
        Parent.objects.bulk_create([Parent(name='parent%d' % i) for i in range(101)])
        self.admin_login(username='super', password='secret')
        self.selenium.get(self.live_server_url + reverse('admin:admin_changelist_parent_changelist'))

        selection_indicator = self.selenium.find_element_by_css_selector('.action-counter')
        select_all_indicator = self.selenium.find_element_by_css_selector('.actions .all')
        question = self.selenium.find_element_by_css_selector('.actions > .question')
        clear = self.selenium.find_element_by_css_selector('.actions > .clear')
        select_all = self.selenium.find_element_by_id('action-toggle')
        select_across = self.selenium.find_elements_by_name('select_across')

        self.assertIs(question.is_displayed(), False)
        self.assertIs(clear.is_displayed(), False)
        self.assertIs(select_all.get_property('checked'), False)
        for hidden_input in select_across:
            self.assertEqual(hidden_input.get_property('value'), '0')
        self.assertIs(selection_indicator.is_displayed(), True)
        self.assertEqual(selection_indicator.text, '0 of 100 selected')
        self.assertIs(select_all_indicator.is_displayed(), False)

        select_all.click()
        self.assertIs(question.is_displayed(), True)
        self.assertIs(clear.is_displayed(), False)
        self.assertIs(select_all.get_property('checked'), True)
        for hidden_input in select_across:
            self.assertEqual(hidden_input.get_property('value'), '0')
        self.assertIs(selection_indicator.is_displayed(), True)
        self.assertEqual(selection_indicator.text, '100 of 100 selected')
        self.assertIs(select_all_indicator.is_displayed(), False)

        question.click()
        self.assertIs(question.is_displayed(), False)
        self.assertIs(clear.is_displayed(), True)
        self.assertIs(select_all.get_property('checked'), True)
        for hidden_input in select_across:
            self.assertEqual(hidden_input.get_property('value'), '1')
        self.assertIs(selection_indicator.is_displayed(), False)
        self.assertIs(select_all_indicator.is_displayed(), True)

        clear.click()
        self.assertIs(question.is_displayed(), False)
        self.assertIs(clear.is_displayed(), False)
        self.assertIs(select_all.get_property('checked'), False)
        for hidden_input in select_across:
            self.assertEqual(hidden_input.get_property('value'), '0')
        self.assertIs(selection_indicator.is_displayed(), True)
        self.assertEqual(selection_indicator.text, '0 of 100 selected')
        self.assertIs(select_all_indicator.is_displayed(), False)

    def test_actions_warn_on_pending_edits(self):
        Parent.objects.create(name='foo')

        self.admin_login(username='super', password='secret')
        self.selenium.get(self.live_server_url + reverse('admin:admin_changelist_parent_changelist'))

        name_input = self.selenium.find_element_by_id('id_form-0-name')
        name_input.clear()
        name_input.send_keys('bar')
        self.selenium.find_element_by_id('action-toggle').click()
        self.selenium.find_element_by_name('index').click()  # Go
        alert = self.selenium.switch_to.alert
        try:
            self.assertEqual(
                alert.text,
                'You have unsaved changes on individual editable fields. If you '
                'run an action, your unsaved changes will be lost.'
            )
        finally:
            alert.dismiss()

    def test_save_with_changes_warns_on_pending_action(self):
        from selenium.webdriver.support.ui import Select

        Parent.objects.create(name='parent')

        self.admin_login(username='super', password='secret')
        self.selenium.get(self.live_server_url + reverse('admin:admin_changelist_parent_changelist'))

        name_input = self.selenium.find_element_by_id('id_form-0-name')
        name_input.clear()
        name_input.send_keys('other name')
        Select(
            self.selenium.find_element_by_name('action')
        ).select_by_value('delete_selected')
        self.selenium.find_element_by_name('_save').click()
        alert = self.selenium.switch_to.alert
        try:
            self.assertEqual(
                alert.text,
                'You have selected an action, but you haven’t saved your '
                'changes to individual fields yet. Please click OK to save. '
                'You’ll need to re-run the action.',
            )
        finally:
            alert.dismiss()

    def test_save_without_changes_warns_on_pending_action(self):
        from selenium.webdriver.support.ui import Select

        Parent.objects.create(name='parent')

        self.admin_login(username='super', password='secret')
        self.selenium.get(self.live_server_url + reverse('admin:admin_changelist_parent_changelist'))

        Select(
            self.selenium.find_element_by_name('action')
        ).select_by_value('delete_selected')
        self.selenium.find_element_by_name('_save').click()
        alert = self.selenium.switch_to.alert
        try:
            self.assertEqual(
                alert.text,
                'You have selected an action, and you haven’t made any '
                'changes on individual fields. You’re probably looking for '
                'the Go button rather than the Save button.',
            )
        finally:
            alert.dismiss()
