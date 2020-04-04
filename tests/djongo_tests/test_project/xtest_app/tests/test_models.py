from xtest_app.models.array_field import ArrayFieldEntry as ArrayEntry, Author as ArrayAuthor
from xtest_app.models.basic_field import Blog, Entry, Author
from xtest_app.models.embedded_field import Blog as EmbeddedBlog, EmbeddedFieldEntry as EmbeddedEntry
from xtest_app.models.misc_field import ListEntry as ListEntry, DictEntry as DictEntry
from xtest_app.models.reference_field import ReferenceEntry as ReferenceEntry, ReferenceAuthor as ReferenceAuthor
from . import TestCase


class TestReference(TestCase):

    def test_create(self):
        e1 = ReferenceEntry.objects.create(
            headline='h1',
        )
        e2 = ReferenceEntry(headline='h2')
        e2.save()

        a1 = ReferenceAuthor.objects.create(
            name='n1',
            email='e1@e1.com'
        )
        a2 = ReferenceAuthor.objects.create(
            name='n2',
            email='e2@e2.com'
        )

        self.assertEqual([], list(e1.authors.all()))
        self.assertEqual([], list(a1.referenceentry_set.all()))

        e1.authors.add(a1)
        self.assertEqual(e1.authors_id, {a1.pk})
        self.assertEqual([a1], list(e1.authors.all()))
        self.assertEqual([e1], list(a1.referenceentry_set.all()))

        e2.authors.add(a1, a2)
        self.assertEqual(e2.authors_id, {a1.pk, a2.pk})
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
        self.assertEqual(e1.authors_id, {a1.pk, a2.pk})
        self.assertEqual([e1, e2], list(a2.referenceentry_set.all()))

        a2.delete()
        self.assertEqual([a1], list(e2.authors.all()))
        self.assertEqual([a1], list(e1.authors.all()))


class TestArray(TestCase):
    def test_create1(self):
        e = ArrayEntry.objects.create(
            headline='h1',
            authors=[ArrayAuthor(
                name='n1',
                email='e1@e1.com'
            )]
        )
        g = ArrayEntry.objects.get(headline='h1')
        self.assertEqual(e, g)
        g.authors.append(
            ArrayAuthor(
                name='n2',
                email='e2@e1.com'
            )
        )
        g.save()
        g = ArrayEntry.objects.get(
            authors={'1.name': 'n2'}
        )
        self.assertEqual(e,g)
        self.assertNotEqual(e.authors, g.authors)


class TestEmbedded(TestCase):

    def test_create(self):
        e = EmbeddedEntry.objects.create(
            headline='h1',
            blog=EmbeddedBlog(
                name='b1',
                tagline='t1'
            )
        )
        g = EmbeddedEntry.objects.get(headline='h1')
        self.assertEqual(e, g)

        g = EmbeddedEntry.objects.get(blog={'name': 'b1'})
        self.assertEqual(e, g)
        self.assertEqual(g.blog.tagline, 't1')
        g.blog.tagline = 't2'
        g.save()
        g = EmbeddedEntry.objects.get(blog={'name': 'b1'})
        self.assertEqual(e, g)
        self.assertEqual(g.blog.tagline, 't2')
        self.assertNotEqual(e.blog.tagline, g.blog.tagline)

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

    def test_create(self):
        b1 = Blog.objects.create(
            name='b1',
            tagline='t1'
        )
        b2 = Blog.objects.create(
            name='b2',
            tagline='t2'
        )
        e1 = Entry.objects.create(
            headline='h1',
            blog=b1
        )
        e2 = Entry.objects.create(
            headline='h2',
            blog=b2
        )
        a1 = Author.objects.create(
            name='a1'
        )
        a2 = Author.objects.create(
            name='a2'
        )
        self.assertEqual([], list(e1.authors.all()))
        self.assertEqual([], list(a1.entry_set.all()))

        e1.authors.add(a1)
        self.assertEqual([a1], list(e1.authors.all()))
        self.assertEqual([e1], list(a1.entry_set.all()))

        e2.authors.add(a1, a2)
        self.assertEqual([a1, a2], list(e2.authors.all()))
        self.assertEqual([e1, e2], list(a1.entry_set.all()))
        self.assertEqual([e2], list(a2.entry_set.all()))

        g = Entry.objects.get(headline='h1')
        self.assertEqual(e1, g)
        g = Entry.objects.get(authors__name='a2')
        self.assertEqual(e2, g)
        g = list(Entry.objects.filter(authors__name='a1'))
        self.assertEqual([e1, e2], g)

        a2.entry_set.add(e1)
        self.assertEqual([e1, e2], list(a2.entry_set.all()))

        a2.delete()
        self.assertEqual([a1], list(e2.authors.all()))
        self.assertEqual([a1], list(e1.authors.all()))

    def test_join(self):
        b1 = Blog.objects.create(
            name='b1',
            tagline='t1'
        )
        b2 = Blog.objects.create(
            name='b2',
            tagline='t2'
        )
        e1 = Entry.objects.create(
            headline='h1',
            blog=b1
        )
        e2 = Entry.objects.create(
            headline='h2',
            blog=b1
        )
        eqs = Entry.objects.filter(blog__name='b1').values('id')
        bqs = Blog.objects.filter(id__in=eqs).values('name')
        self.assertEquals(list(bqs), [{'name': 'b1'}, {'name': 'b2'}])


class TestMisc(TestCase):

    def test_create(self):
        e1 = ListEntry()
        e1.authors = ['a1', 'a2']
        e1.headline = 'h1'
        e1.save()
        g = ListEntry.objects.get(
            headline='h1'
        )
        self.assertEqual(e1, g)

        # g = ListEntry.objects.get(
        #     authors={'0.': 'a1'}
        # )
        self.assertEqual(e1, g)
        e2 = DictEntry()
        e2.headline = 'h2'
        e2.blog = {
            'name': 'b1'
        }
        e2.save()
        g = DictEntry.objects.get(
            headline='h2'
        )
        self.assertEqual(e2, g)
        g = DictEntry.objects.get(
            blog={'name': 'b1'}
        )
        self.assertEqual(e2, g)
