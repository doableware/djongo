from logging import getLogger, StreamHandler, DEBUG
from django.core import management
from . import TestCase
from dummy.models import Dummy
from django.contrib.auth.models import User


root_logger = getLogger()
root_logger.setLevel(DEBUG)
root_logger.addHandler(StreamHandler())
# class Test(models.Model):
#     test = models.CharField(max_length=10)

class TestWithDjango(TestCase):

    def test_models(self):

        test = Dummy(test='test data')
        test.save()
        tdel = Dummy.objects.get(test='test data')

    def test_admin(self):

        u = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        u.save()
        management.call_command('runserver')
        management.call_command('runserver')