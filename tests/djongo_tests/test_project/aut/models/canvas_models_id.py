import json

# from django.db import models
from djongo import models

#
# class ForeignKey1(models.Model):
#     objects = models.DjongoManager()
#     _id = models.ObjectIdField()
#     name = models.TextField(unique=True)
#
#     @classmethod
#     def create(cls, *args, **kwargs):
#         new_instance = cls(*args, **kwargs)
#
#         return new_instance
#
#     def __str__(self):
#         return self.to_json()
#
#     def to_json(self):
#         return json.dumps(self.to_dict())
#
#     def to_dict(self):
#         return {
#             "_id": str(self._id),
#             "name": self.name
#         }
#
#
# class ForeignKey2(models.Model):
#     objects = models.DjongoManager()
#     _id = models.ObjectIdField()
#     name = models.TextField(unique=True)
#
#     @classmethod
#     def create(cls, *args, **kwargs):
#         new_instance = cls(*args, **kwargs)
#
#         return new_instance
#
#     def __str__(self):
#         return self.to_json()
#
#     def to_json(self):
#         return json.dumps(self.to_dict())
#
#     def to_dict(self):
#         return {
#             "_id": str(self._id),
#             "name": self.name
#         }
#
#
# class DummyObject(models.Model):
#     _id = models.ObjectIdField()
#     foreign_key_1 = models.ForeignKey(ForeignKey1, on_delete=models.PROTECT)
#     foreign_key_2 = models.ForeignKey(ForeignKey2, on_delete=models.PROTECT)
#
#     def __str__(self):
#         return self.to_json()
#
#     def to_json(self):
#         return json.dumps(self.to_dict())
#
#     def to_dict(self):
#         return {
#             "_id": str(self._id),
#             "foreign_key_1": self.foreign_key_1.to_dict(),
#             "foreign_key_2": self.foreign_key_2.to_dict()
#         }
#
#     @classmethod
#     def create(cls, *args, **kwargs):
#         new_instance = cls(*args, **kwargs)
#
#         return new_instance