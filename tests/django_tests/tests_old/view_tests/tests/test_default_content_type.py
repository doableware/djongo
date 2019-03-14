import sys
from types import ModuleType

from django.conf import Settings
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango30Warning


class DefaultContentTypeTests(SimpleTestCase):
    msg = 'The DEFAULT_CONTENT_TYPE setting is deprecated.'

    @ignore_warnings(category=RemovedInDjango30Warning)
    def test_default_content_type_is_text_html(self):
        """
        Content-Type of the default error responses is text/html. Refs #20822.
        """
        with self.settings(DEFAULT_CONTENT_TYPE='text/xml'):
            response = self.client.get('/raises400/')
            self.assertEqual(response['Content-Type'], 'text/html')

            response = self.client.get('/raises403/')
            self.assertEqual(response['Content-Type'], 'text/html')

            response = self.client.get('/nonexistent_url/')
            self.assertEqual(response['Content-Type'], 'text/html')

            response = self.client.get('/server_error/')
            self.assertEqual(response['Content-Type'], 'text/html')

    def test_override_settings_warning(self):
        with self.assertRaisesMessage(RemovedInDjango30Warning, self.msg):
            with self.settings(DEFAULT_CONTENT_TYPE='text/xml'):
                pass

    def test_settings_init_warning(self):
        settings_module = ModuleType('fake_settings_module')
        settings_module.DEFAULT_CONTENT_TYPE = 'text/xml'
        settings_module.SECRET_KEY = 'abc'
        sys.modules['fake_settings_module'] = settings_module
        try:
            with self.assertRaisesMessage(RemovedInDjango30Warning, self.msg):
                Settings('fake_settings_module')
        finally:
            del sys.modules['fake_settings_module']
