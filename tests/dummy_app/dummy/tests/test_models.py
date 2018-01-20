from django.db.models import Count

from . import TestCase
from dummy.basic_models import Blog, Entry, Author
from django.contrib.auth.models import User


class TestWithDjango(TestCase):

    @classmethod
    def setUpClass(cls):
        b1 = Blog(name='b1', tagline='t1')
        b1.save()
        b2 = Blog(name='b2', tagline='t2')
        b2.save()
        b3 = Blog(name='b3', tagline='t3')
        b3.save()

        a1 = Author(name='a1')
        a1.save()
        a2 = Author(name='a2')
        a2.save()

        e1 = Entry(headline='h1', blog=b1)
        e1.save()
        e1.authors.add(a1, a2)

        e2 = Entry(headline='h2', blog=b1)
        e2.save()
        e2.authors.add(a1, a2)


    def test_join(self):
        bqs = Blog.objects.filter(name='b1')
        bqs.entry_set.filter(headline__startswith='h')
        eqs = Entry.objects.filter(blog__in=bqs)

    def test_models(self):
        tdel = BlogPost.objects.get(h1='test data')
        inner_qs = BlogPost.objects.filter(h1__contains='test')

    def test_query(self):
        qs = BlogPost.objects.filter(h1__contains='a').exists()
        qs = BlogPost.objects.filter(h1__contains='hell').count()

        qs = BlogPost.objects.filter(h1__contains='hell').distinct()
        o = list(qs)
        qs = MultipleBlogPosts.objects.annotate(Count('h1'), Count('content'))
        o = list(qs)

