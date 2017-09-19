from django.core import management
from django.test import TestCase
from dummy.models import Dummy


# class Test(models.Model):
#     test = models.CharField(max_length=10)

class TestWithDjango(TestCase):

    def test_models(self):

        test = Dummy(test='test data')
        test.save()
        tdel = Dummy.objects.get(test='test data')
        print('shimataa')