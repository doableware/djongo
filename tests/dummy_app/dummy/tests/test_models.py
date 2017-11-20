from logging import getLogger, StreamHandler, DEBUG
from django.core import management
from . import TestCase
from dummy.models import BlogPost, BlogContent, MultipleBlogPosts
from django.contrib.auth.models import User


class TestWithDjango(TestCase):

    def test_models(self):
        content = BlogContent(comment='embedded text', author='embedded')
        test = BlogPost(h1='test data', content=content)
        test.save()
        tdel = BlogPost.objects.get(h1='test data')
        embedded_array = MultipleBlogPosts(h1='heading', content=[content, content])
        embedded_array.save()
        tdel.delete()

    # def test_admin(self):
    #
    #     u = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
    #     u.save()
    #     management.call_command('runserver')
    #     management.call_command('runserver')