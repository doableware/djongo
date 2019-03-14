from django.contrib import admin
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from .models import Band


class AdminActionsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(username='super', password='secret', email='super@example.com')
        content_type = ContentType.objects.get_for_model(Band)
        Permission.objects.create(name='custom', codename='custom_band', content_type=content_type)
        for user_type in ('view', 'add', 'change', 'delete', 'custom'):
            username = '%suser' % user_type
            user = User.objects.create_user(username=username, password='secret', is_staff=True)
            permission = Permission.objects.get(codename='%s_band' % user_type, content_type=content_type)
            user.user_permissions.add(permission)
            setattr(cls, username, user)

    def test_get_actions_respects_permissions(self):
        class MockRequest:
            pass

        class BandAdmin(admin.ModelAdmin):
            actions = ['custom_action']

            def custom_action(modeladmin, request, queryset):
                pass

            def has_custom_permission(self, request):
                return request.user.has_perm('%s.custom_band' % self.opts.app_label)

        ma = BandAdmin(Band, admin.AdminSite())
        mock_request = MockRequest()
        mock_request.GET = {}
        cases = [
            (None, self.viewuser, ['custom_action']),
            ('view', self.superuser, ['delete_selected', 'custom_action']),
            ('view', self.viewuser, ['custom_action']),
            ('add', self.adduser, ['custom_action']),
            ('change', self.changeuser, ['custom_action']),
            ('delete', self.deleteuser, ['delete_selected', 'custom_action']),
            ('custom', self.customuser, ['custom_action']),
        ]
        for permission, user, expected in cases:
            with self.subTest(permission=permission, user=user):
                if permission is None:
                    if hasattr(BandAdmin.custom_action, 'allowed_permissions'):
                        del BandAdmin.custom_action.allowed_permissions
                else:
                    BandAdmin.custom_action.allowed_permissions = (permission,)
                mock_request.user = user
                actions = ma.get_actions(mock_request)
                self.assertEqual(list(actions.keys()), expected)
