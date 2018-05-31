from . import TestCase
from dummy.models.basic_models import Blog, Entry, Author
from dummy.models.basic_embedded_models import EmbeddedBlog, EmbeddedEntry
from dummy.models.basic_reference_models import ReferenceEntry, ReferenceAuthor

class TestReference(TestCase):

    def test_create(self):
        e1 = ReferenceEntry.objects.create(
            headline='h1',
        )
        e2 = ReferenceEntry.objects.create(
            headline='h2',
        )
        a1 = ReferenceAuthor.objects.create(
            name='n1',
            email='e1@e1.com'
        )
        a2 = ReferenceAuthor.objects.create(
            name='n2',
            email='e2@e2.com'
        )

        e1.authors.add(a1)
        self.assertEqual([a1], list(e1.authors.all()))
        self.assertEqual([e1], list(a1.referenceentry_set.all()))

        e2.authors.add(a1,a2)
        self.assertEqual([a1, a2], list(e2.authors.all()))
        self.assertEqual([e1, e2], list(a1.referenceentry_set.all()))
        self.assertEqual([e2], list(a2.referenceentry_set.all()))

        g = ReferenceEntry.objects.get(headline='h1')
        self.assertEqual(e1, g)
        g = ReferenceEntry.objects.get(authors__name='n2')
        self.assertEqual(e2, g)
        g = list(ReferenceEntry.objects.filter(authors__name='n1'))
        self.assertEqual([e1, e2], g)

        a2.referenceentry_set.add(e1)
        self.assertEqual([e1, e2], list(a2.referenceentry_set.all()))

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


class TestBasic(TestCase):

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
        eqs = Entry.objects.filter(blog__name='b1').values('id')
        bqs = Blog.objects.filter(id__in=eqs).values('name')
        self.assertEquals(list(bqs), [{'name': 'b1'}, {'name': 'b2'}])
        print('done')


