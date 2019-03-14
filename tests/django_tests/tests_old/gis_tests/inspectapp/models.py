from django.contrib.gis.db import models


class AllOGRFields(models.Model):

    f_decimal = models.FloatField()
    f_float = models.FloatField()
    f_int = models.IntegerField()
    f_char = models.CharField(max_length=10)
    f_date = models.DateField()
    f_datetime = models.DateTimeField()
    f_time = models.TimeField()
    geom = models.PolygonField()
    point = models.PointField()


class Fields3D(models.Model):
    point = models.PointField(dim=3)
    pointg = models.PointField(dim=3, geography=True)
    line = models.LineStringField(dim=3)
    poly = models.PolygonField(dim=3)
