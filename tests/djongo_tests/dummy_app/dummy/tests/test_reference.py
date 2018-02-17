from . import TestCase
from dummy.basic_reference_models import ReferenceEntry, ReferenceAuthor


class TestWithDjango(TestCase):

    @classmethod
    def setUpClass(cls):
        a1 = ReferenceAuthor(name='a1')
        a1.save()

        e1 = ReferenceEntry()
        e1.save()
        e1.authors.add(a1)
        list(ReferenceEntry.objects.filter(authors__name='a1'))
        list(e1.authors.all())
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


