from django.db.models import QuerySet

from . import TestCase
from djongo import models

class Team(models.Model):
    id = models.TextField()
    extra = models.JSONField(null=True)

    class Meta:
        abstract = True

class DocumentQuerySet(QuerySet):
    def from_team(self, team_id: str):
        return self.filter(team={'id': team_id})

class Document(models.Model):
    team = models.EmbeddedField(model_container=Team)
    objects = models.DjongoManager.from_queryset(DocumentQuerySet)()

class Document2(models.Model):
    team = models.CharField(max_length=10)
    objects = models.DjongoManager.from_queryset(DocumentQuerySet)()

class TestCanvas(TestCase):

    def test_canvas(self):
        entry = Document.objects.create(
            team={'id': 'an id', 'extra': {'a': 1}}
        )
        b_entry = Document.objects.from_team('an id')
        print(b_entry)
