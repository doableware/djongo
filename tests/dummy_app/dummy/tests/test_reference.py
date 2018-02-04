from django.db.models import Count

from . import TestCase
from dummy.basic_reference_models import ReferenceEntry, ReferenceAuthor
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
        eqs = Entry.objects.filter(blog__name='b1').values('id')
        bqs = Blog.objects.filter(id__in=eqs).values('name')
        self.assertEquals(list(bqs), [{'name': 'b1'}, {'name': 'b2'}])
        print('done')


