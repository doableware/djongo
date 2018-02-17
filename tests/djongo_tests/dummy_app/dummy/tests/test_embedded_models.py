from django.db.models import Count

from . import TestCase
from dummy.basic_embedded_models import EBlog, EEntry, EAuthor
from django.contrib.auth.models import User


class TestWithDjango(TestCase):

    @classmethod
    def setUpClass(cls):
        b1 = EBlog(name='b1', tagline='t1')
        b2 = EBlog(name='b2', tagline='t2')
        b3 = EBlog(name='b3', tagline='t3')

        a1 = EAuthor(name='a1')
        a1.save()
        a2 = EAuthor(name='a2')
        a2.save()

        e1 = Entry(headline='h1', blog=b1)
        e1.save()
        e1.authors.add(a1, a2)

        e2 = Entry(headline='h2', blog=b1)
        e2.save()
        e2.authors.add(a1, a2)


    def test_join(self):
        eqs = Entry.objects.filter(blog__name='b1').values('id')
        bqs = Blog.objects.filter(id__in=eqs).values('name')
        self.assertEquals(list(bqs), [{'name': 'b1'}, {'name': 'b2'}])
        print('done')

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

