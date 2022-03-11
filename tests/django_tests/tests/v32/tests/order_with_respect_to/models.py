"""
Tests for the order_with_respect_to Meta attribute.
"""

from django.db import models


class Question(models.Model):
    text = models.CharField(max_length=200)


class Answer(models.Model):
    text = models.CharField(max_length=200)
    question = models.ForeignKey(Question, models.CASCADE)

    class Meta:
        order_with_respect_to = 'question'

    def __str__(self):
        return self.text


class Post(models.Model):
    title = models.CharField(max_length=200)
    parent = models.ForeignKey("self", models.SET_NULL, related_name="children", null=True)

    class Meta:
        order_with_respect_to = "parent"

    def __str__(self):
        return self.title


# order_with_respect_to points to a model with a OneToOneField primary key.
class Entity(models.Model):
    pass


class Dimension(models.Model):
    entity = models.OneToOneField('Entity', primary_key=True, on_delete=models.CASCADE)


class Component(models.Model):
    dimension = models.ForeignKey('Dimension', on_delete=models.CASCADE)

    class Meta:
        order_with_respect_to = 'dimension'
