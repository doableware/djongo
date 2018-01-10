from django.db.models import Count

from . import TestCase
from dummy.models import BlogPost, BlogContent, MultipleBlogPosts, Author
from django.contrib.auth.models import User


class TestWithDjango(TestCase):

    def test_models(self):
        author = Author(name='nes', email='nes@mail.com')
        content = BlogContent(comment='embedded text', author=author)
        test = BlogPost(h1='test data', content=content)
        test.save()
        tdel = BlogPost.objects.get(h1='test data')
        inner_qs = BlogPost.objects.filter(h1__contains='test')
        o = list(inner_qs)

        embedded_array = MultipleBlogPosts(h1='heading', content=[content, content])
        embedded_array.save()
        tdel.delete()

    def test_query(self):
        inner_qs = BlogPost.objects.filter(h1__contains='a')
        o = list(inner_qs)
        qs = MultipleBlogPosts.objects.annotate(Count('h1'), Count('content'))
        o = list(qs)

    # def test_admin(self):
    #
    #     u = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
    #     u.save()
    #     management.call_command('runserver')
    #     management.call_command('runserver')