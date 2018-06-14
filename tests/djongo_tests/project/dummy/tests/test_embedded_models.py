from django.db.models import Count

from . import TestCase
from dummy.models.basic_embedded_models import EmbeddedBlog, EmbeddedEntry



class TestEmbedded(TestCase):

    @classmethod
    def setUpClass(cls):
        # b1 = EmbeddedBlog(name='b1', tagline='t1')
        # b2 = EmbeddedBlog(name='b2', tagline='t2')
        # b3 = EmbeddedBlog(name='b3', tagline='t3')
        #
        # e1 = EmbeddedEntry(headline='h1', blog=b1)
        # e1.save()
        pass

    def test_create(self):
        e = EmbeddedEntry.objects.create(
            headline='h1',
            blog=EmbeddedBlog(name='b1', tagline='t1')
        )
        g = EmbeddedEntry.objects.get(headline='h1')
        self.assertEqual(e, g)

        g = EmbeddedEntry.objects.get(blog={'name': 'b1'})
        self.assertEqual(e, g)

    # def test_join(self):
    #     eqs = EmbeddedEntry.objects.filter(blog__name='b1').values('id')
    #     bqs = EmbeddedBlog.objects.filter(id__in=eqs).values('name')
    #     self.assertEquals(list(bqs), [{'name': 'b1'}, {'name': 'b2'}])
    #     print('done')
    #
    # def test_models(self):
    #     tdel = BlogPost.objects.get(h1='test data')
    #     inner_qs = BlogPost.objects.filter(h1__contains='test')
    #
    # def test_query(self):
    #     qs = BlogPost.objects.filter(h1__contains='a').exists()
    #     qs = BlogPost.objects.filter(h1__contains='hell').count()
    #
    #     qs = BlogPost.objects.filter(h1__contains='hell').distinct()
    #     o = list(qs)
    #     qs = MultipleBlogPosts.objects.annotate(Count('h1'), Count('content'))
    #     o = list(qs)

