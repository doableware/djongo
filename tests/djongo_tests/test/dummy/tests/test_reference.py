from . import TestCase
from dummy.models.basic_reference_models import ReferenceEntry, ReferenceAuthor


class TestWithDjango(TestCase):

    @classmethod
    def setUpClass(cls):
        a1 = ReferenceAuthor(name='a1')
        a1.save()
        a2 = ReferenceAuthor(name='a2')
        a2.save()

        e1 = ReferenceEntry(headline='h1')
        e1.save()
        e2 = ReferenceEntry(headline='h2')
        e2.save()
        e1.authors.add(a1, a2)
        e2.authors.add(a2)
        print(list(ReferenceEntry.objects.filter(authors__name='a1')))
        print(list(e1.authors.all()))
        print(list(ReferenceEntry.objects.filter(authors__name='a2')))
        print(list(e2.authors.all()))
        e1.authors.filter()
        e1.authors.add(a1)
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


