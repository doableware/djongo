from django.test import TestCase

from .models import Person


class PropertyTests(TestCase):

    def setUp(self):
        self.a = Person(first_name='John', last_name='Lennon')
        self.a.save()

    def test_getter(self):
        self.assertEqual(self.a.full_name, 'John Lennon')

    def test_setter(self):
        # The "full_name" property hasn't provided a "set" method.
        with self.assertRaises(AttributeError):
            setattr(self.a, 'full_name', 'Paul McCartney')

        # And cannot be used to initialize the class.
        with self.assertRaisesMessage(TypeError, "'full_name' is an invalid keyword argument"):
            Person(full_name='Paul McCartney')

        # But "full_name_2" has, and it can be used to initialize the class.
        a2 = Person(full_name_2='Paul McCartney')
        a2.save()
        self.assertEqual(a2.first_name, 'Paul')
