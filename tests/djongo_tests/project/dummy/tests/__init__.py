from django.test import TestCase as DjangoTestCase
from logging import getLogger, StreamHandler

class TestCase(DjangoTestCase):

    @classmethod
    def setUpClass(cls):
        root_logger = getLogger()
        root_logger.addHandler(StreamHandler())
        super().setUpClass()
