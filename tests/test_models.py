from django.test import TestCase
from djongo import models
import os

# os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'
class TestWithDjango(TestCase):

    def test_models(self):
        class Test(models.Model):
            test = models.CharField(max_length=10)

        test = Test(test='test')
        test.save()
        print('shimata')
        