from django.test import TransactionTestCase
from threading import Thread

from xtest_app.models.canvas_models_id import ForeignKey1, ForeignKey2, DummyObject

def make_request():
    objects = DummyObject.objects.all()

    print(objects)

class MetaScanConcurrencyTest(TransactionTestCase):
    def setUp(self):
        foreign_key_1 = ForeignKey1.create(**{
            "name": "foreign_key_1"
        })

        foreign_key_2 = ForeignKey2.create(**{
            "name": "foreign_key_2"
        })

        foreign_key_1.save()
        foreign_key_2.save()

        for i in range(0, 1):
            dummy = DummyObject.create(**{
                "foreign_key_1": foreign_key_1,
                "foreign_key_2": foreign_key_2
            })

            dummy.save()

    def test_concurrency_test(self):
        threads = []
        for i in range(0, 100):
            t = Thread(target=make_request)
            threads.append(t)
            t.start()
            # Thread(target=make_request).start()

        for thread in threads:
            thread.join()
        # objects = DummyObject.objects.all()
        #
        # print(objects)