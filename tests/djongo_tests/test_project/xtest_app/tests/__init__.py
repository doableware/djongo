from logging import getLogger, StreamHandler

from django.test import TestCase as DjangoTestCase


class TestCase(DjangoTestCase):

    @classmethod
    def setUpClass(cls):
        root_logger = getLogger()
        if not root_logger.hasHandlers():
            root_logger.addHandler(StreamHandler())
