from django.test import SimpleTestCase, override_settings
from django.test.utils import require_jinja2


@override_settings(ROOT_URLCONF='shortcuts.urls')
class RenderTests(SimpleTestCase):

    def test_render(self):
        response = self.client.get('/render/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'FOO.BAR../render/\n')
        self.assertEqual(response.headers['Content-Type'], 'text/html; charset=utf-8')
        self.assertFalse(hasattr(response.context.request, 'current_app'))

    def test_render_with_multiple_templates(self):
        response = self.client.get('/render/multiple_templates/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'FOO.BAR../render/multiple_templates/\n')

    def test_render_with_content_type(self):
        response = self.client.get('/render/content_type/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'FOO.BAR../render/content_type/\n')
        self.assertEqual(response.headers['Content-Type'], 'application/x-rendertest')

    def test_render_with_status(self):
        response = self.client.get('/render/status/')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, b'FOO.BAR../render/status/\n')

    @require_jinja2
    def test_render_with_using(self):
        response = self.client.get('/render/using/')
        self.assertEqual(response.content, b'DTL\n')
        response = self.client.get('/render/using/?using=django')
        self.assertEqual(response.content, b'DTL\n')
        response = self.client.get('/render/using/?using=jinja2')
        self.assertEqual(response.content, b'Jinja2\n')
