from functools import wraps

from django.db import IntegrityError, connections, transaction
from django.test import TestCase, ignore_warnings, skipUnlessDBFeature
from django.test.testcases import TestData
from django.utils.deprecation import RemovedInDjango41Warning

from .models import Car, Person, PossessedCar


class TestTestCase(TestCase):

    @skipUnlessDBFeature('can_defer_constraint_checks')
    @skipUnlessDBFeature('supports_foreign_keys')
    def test_fixture_teardown_checks_constraints(self):
        rollback_atomics = self._rollback_atomics
        self._rollback_atomics = lambda connection: None  # noop
        try:
            car = PossessedCar.objects.create(car_id=1, belongs_to_id=1)
            with self.assertRaises(IntegrityError), transaction.atomic():
                self._fixture_teardown()
            car.delete()
        finally:
            self._rollback_atomics = rollback_atomics

    def test_disallowed_database_connection(self):
        message = (
            "Database connections to 'other' are not allowed in this test. "
            "Add 'other' to test_utils.test_testcase.TestTestCase.databases to "
            "ensure proper test isolation and silence this failure."
        )
        with self.assertRaisesMessage(AssertionError, message):
            connections['other'].connect()
        with self.assertRaisesMessage(AssertionError, message):
            connections['other'].temporary_connection()

    def test_disallowed_database_queries(self):
        message = (
            "Database queries to 'other' are not allowed in this test. "
            "Add 'other' to test_utils.test_testcase.TestTestCase.databases to "
            "ensure proper test isolation and silence this failure."
        )
        with self.assertRaisesMessage(AssertionError, message):
            Car.objects.using('other').get()


class NonDeepCopyAble:
    def __deepcopy__(self, memo):
        raise TypeError


def assert_no_queries(test):
    @wraps(test)
    def inner(self):
        with self.assertNumQueries(0):
            test(self)
    return inner


class TestDataTests(TestCase):
    # setUpTestData re-assignment are also wrapped in TestData.
    jim_douglas = None

    @classmethod
    def setUpTestData(cls):
        cls.jim_douglas = Person.objects.create(name='Jim Douglas')
        cls.car = Car.objects.create(name='1963 Volkswagen Beetle')
        cls.herbie = cls.jim_douglas.possessed_cars.create(
            car=cls.car,
            belongs_to=cls.jim_douglas,
        )
        cls.non_deepcopy_able = NonDeepCopyAble()

        cls.person_binary = Person.objects.create(name='Person', data=b'binary data')
        cls.person_binary_get = Person.objects.get(pk=cls.person_binary.pk)

    @assert_no_queries
    def test_class_attribute_equality(self):
        """Class level test data is equal to instance level test data."""
        self.assertEqual(self.jim_douglas, self.__class__.jim_douglas)
        self.assertEqual(self.person_binary, self.__class__.person_binary)
        self.assertEqual(self.person_binary_get, self.__class__.person_binary_get)

    @assert_no_queries
    def test_class_attribute_identity(self):
        """
        Class level test data is not identical to instance level test data.
        """
        self.assertIsNot(self.jim_douglas, self.__class__.jim_douglas)
        self.assertIsNot(self.person_binary, self.__class__.person_binary)
        self.assertIsNot(self.person_binary_get, self.__class__.person_binary_get)

    @assert_no_queries
    def test_binaryfield_data_type(self):
        self.assertEqual(bytes(self.person_binary.data), b'binary data')
        self.assertEqual(bytes(self.person_binary_get.data), b'binary data')
        self.assertEqual(
            type(self.person_binary_get.data),
            type(self.__class__.person_binary_get.data),
        )
        self.assertEqual(
            type(self.person_binary.data),
            type(self.__class__.person_binary.data),
        )

    @assert_no_queries
    def test_identity_preservation(self):
        """Identity of test data is preserved between accesses."""
        self.assertIs(self.jim_douglas, self.jim_douglas)

    @assert_no_queries
    def test_known_related_objects_identity_preservation(self):
        """Known related objects identity is preserved."""
        self.assertIs(self.herbie.car, self.car)
        self.assertIs(self.herbie.belongs_to, self.jim_douglas)

    @ignore_warnings(category=RemovedInDjango41Warning)
    def test_undeepcopyable(self):
        self.assertIs(self.non_deepcopy_able, self.__class__.non_deepcopy_able)

    def test_undeepcopyable_warning(self):
        msg = (
            "Assigning objects which don't support copy.deepcopy() during "
            "setUpTestData() is deprecated. Either assign the "
            "non_deepcopy_able attribute during setUpClass() or setUp(), or "
            "add support for deepcopy() to "
            "test_utils.test_testcase.TestDataTests.non_deepcopy_able."
        )
        with self.assertRaisesMessage(RemovedInDjango41Warning, msg):
            self.non_deepcopy_able

    def test_repr(self):
        self.assertEqual(
            repr(TestData('attr', 'value')),
            "<TestData: name='attr', data='value'>",
        )


class SetupTestDataIsolationTests(TestCase):
    """
    In-memory data isolation is respected for model instances assigned to class
    attributes during setUpTestData.
    """
    @classmethod
    def setUpTestData(cls):
        cls.car = Car.objects.create(name='Volkswagen Beetle')

    def test_book_name_deutsh(self):
        self.assertEqual(self.car.name, 'Volkswagen Beetle')
        self.car.name = 'VW sKäfer'
        self.car.save()

    def test_book_name_french(self):
        self.assertEqual(self.car.name, 'Volkswagen Beetle')
        self.car.name = 'Volkswagen Coccinelle'
        self.car.save()
