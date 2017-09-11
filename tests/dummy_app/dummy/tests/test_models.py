from django.core import management
from django.test import TestCase
from django.db import models

import os

# os.environ['DJANGO_SETTINGS_MODULE'] = 'dummy_app.settings'
class TestWithDjango(TestCase):

    def test_models(self):
        class Test(models.Model):
            test = models.CharField(max_length=10)

        test = Test(test='test')
        test.save()
        print('shimataa')