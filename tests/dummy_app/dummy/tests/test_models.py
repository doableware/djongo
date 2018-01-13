from django.db.models import Count

from . import TestCase
from dummy.models import BlogPost, BlogContentSimple, MultipleBlogPosts, Author
from django.contrib.auth.models import User


class TestWithDjango(TestCase):

    @classmethod
    def setUpClass(cls):
        content = BlogContentSimple(comment='hello world1', author='nes1')
        test = BlogPost(h1='hello1', content=content)
        test.save()
        content = BlogContentSimple(comment='hello world2', author='nes2')
        test = BlogPost(h1='hello2', content=content)
        test.save()
        content = BlogContentSimple(comment='hello world3', author='nes3')
        test = BlogPost(h1='hello3', content=content)
        test.save()
        content = BlogContentSimple(comment='hello world4', author='nes4')
        test = BlogPost(h1='hello4', content=content)
        test.save()

    def test_models(self):
        tdel = BlogPost.objects.get(h1='test data')
        inner_qs = BlogPost.objects.filter(h1__contains='test')

    def test_query(self):
        qs = BlogPost.objects.filter(h1__contains='a').exists()
        qs = BlogPost.objects.filter(h1__contains='hell').count()

        qs = BlogPost.objects.filter(h1__contains='a').distinct()
        o = list(qs)
        qs = MultipleBlogPosts.objects.annotate(Count('h1'), Count('content'))
        o = list(qs)

