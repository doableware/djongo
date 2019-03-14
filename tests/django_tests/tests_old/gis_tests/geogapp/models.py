from django.contrib.gis.db import models


class NamedModel(models.Model):
    name = models.CharField(max_length=30)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class City(NamedModel):
    point = models.PointField(geography=True)

    class Meta:
        app_label = 'geogapp'


class Zipcode(NamedModel):
    code = models.CharField(max_length=10)
    poly = models.PolygonField(geography=True)


class County(NamedModel):
    state = models.CharField(max_length=20)
    mpoly = models.MultiPolygonField(geography=True)

    class Meta:
        app_label = 'geogapp'

    def __str__(self):
        return ' County, '.join([self.name, self.state])
