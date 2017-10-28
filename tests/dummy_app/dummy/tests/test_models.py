from logging import getLogger, StreamHandler, DEBUG
from django.core import management
from . import TestCase
from dummy.models import Dummy, Embedded
from django.contrib.auth.models import User


class TestWithDjango(TestCase):

    def test_models(self):
        embedded = Embedded(text='embedded text')
        test = Dummy(test='test data', embedded=embedded)
        test.save()
        tdel = Dummy.objects.get(test='test data')

    # def test_admin(self):
    #
    #     u = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
    #     u.save()
    #     management.call_command('runserver')
    #     management.call_command('runserver')