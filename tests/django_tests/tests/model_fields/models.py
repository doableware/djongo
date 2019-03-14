import os
import tempfile
import uuid

from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models.fields.files import ImageField, ImageFieldFile
from django.db.models.fields.related import (
    ForeignKey, ForeignObject, ManyToManyField, OneToOneField,
)

try:
    from PIL import Image
except ImportError:
    Image = None


class Foo(models.Model):
    a = models.CharField(max_length=10)
    d = models.DecimalField(max_digits=5, decimal_places=3)


def get_foo():
    return Foo.objects.get(id=1).pk


class Bar(models.Model):
    b = models.CharField(max_length=10)
    a = models.ForeignKey(Foo, models.CASCADE, default=get_foo, related_name='bars')


class Whiz(models.Model):
    CHOICES = (
        ('Group 1', (
            (1, 'First'),
            (2, 'Second'),
        )
        ),
        ('Group 2', (
            (3, 'Third'),
            (4, 'Fourth'),
        )
        ),
        (0, 'Other'),
    )
    c = models.IntegerField(choices=CHOICES, null=True)


class WhizIter(models.Model):
    c = models.IntegerField(choices=iter(Whiz.CHOICES), null=True)


class WhizIterEmpty(models.Model):
    c = models.CharField(choices=iter(()), blank=True, max_length=1)


class BigD(models.Model):
    d = models.DecimalField(max_digits=32, decimal_places=30)


class FloatModel(models.Model):
    size = models.FloatField()


class BigS(models.Model):
    s = models.SlugField(max_length=255)


class UnicodeSlugField(models.Model):
    s = models.SlugField(max_length=255, allow_unicode=True)


class SmallIntegerModel(models.Model):
    value = models.SmallIntegerField()


class IntegerModel(models.Model):
    value = models.IntegerField()


class BigIntegerModel(models.Model):
    value = models.BigIntegerField()
    null_value = models.BigIntegerField(null=True, blank=True)


class PositiveSmallIntegerModel(models.Model):
    value = models.PositiveSmallIntegerField()


class PositiveIntegerModel(models.Model):
    value = models.PositiveIntegerField()


class Post(models.Model):
    title = models.CharField(max_length=100)
    body = models.TextField()


class NullBooleanModel(models.Model):
    nbfield = models.BooleanField(null=True, blank=True)
    nbfield_old = models.NullBooleanField()


class BooleanModel(models.Model):
    bfield = models.BooleanField()
    string = models.CharField(max_length=10, default='abc')


class DateTimeModel(models.Model):
    d = models.DateField()
    dt = models.DateTimeField()
    t = models.TimeField()


class DurationModel(models.Model):
    field = models.DurationField()


class NullDurationModel(models.Model):
    field = models.DurationField(null=True)


class PrimaryKeyCharModel(models.Model):
    string = models.CharField(max_length=10, primary_key=True)


class FksToBooleans(models.Model):
    """Model with FKs to models with {Null,}BooleanField's, #15040"""
    bf = models.ForeignKey(BooleanModel, models.CASCADE)
    nbf = models.ForeignKey(NullBooleanModel, models.CASCADE)


class FkToChar(models.Model):
    """Model with FK to a model with a CharField primary key, #19299"""
    out = models.ForeignKey(PrimaryKeyCharModel, models.CASCADE)


class RenamedField(models.Model):
    modelname = models.IntegerField(name="fieldname", choices=((1, 'One'),))


class VerboseNameField(models.Model):
    id = models.AutoField("verbose pk", primary_key=True)
    field1 = models.BigIntegerField("verbose field1")
    field2 = models.BooleanField("verbose field2", default=False)
    field3 = models.CharField("verbose field3", max_length=10)
    field4 = models.DateField("verbose field4")
    field5 = models.DateTimeField("verbose field5")
    field6 = models.DecimalField("verbose field6", max_digits=6, decimal_places=1)
    field7 = models.EmailField("verbose field7")
    field8 = models.FileField("verbose field8", upload_to="unused")
    field9 = models.FilePathField("verbose field9")
    field10 = models.FloatField("verbose field10")
    # Don't want to depend on Pillow in this test
    # field_image = models.ImageField("verbose field")
    field11 = models.IntegerField("verbose field11")
    field12 = models.GenericIPAddressField("verbose field12", protocol="ipv4")
    field13 = models.NullBooleanField("verbose field13")
    field14 = models.PositiveIntegerField("verbose field14")
    field15 = models.PositiveSmallIntegerField("verbose field15")
    field16 = models.SlugField("verbose field16")
    field17 = models.SmallIntegerField("verbose field17")
    field18 = models.TextField("verbose field18")
    field19 = models.TimeField("verbose field19")
    field20 = models.URLField("verbose field20")
    field21 = models.UUIDField("verbose field21")
    field22 = models.DurationField("verbose field22")


class GenericIPAddress(models.Model):
    ip = models.GenericIPAddressField(null=True, protocol='ipv4')


###############################################################################
# These models aren't used in any test, just here to ensure they validate
# successfully.

# See ticket #16570.
class DecimalLessThanOne(models.Model):
    d = models.DecimalField(max_digits=3, decimal_places=3)


# See ticket #18389.
class FieldClassAttributeModel(models.Model):
    field_class = models.CharField

###############################################################################


class DataModel(models.Model):
    short_data = models.BinaryField(max_length=10, default=b'\x08')
    data = models.BinaryField()

###############################################################################
# FileField


class Document(models.Model):
    myfile = models.FileField(upload_to='unused', unique=True)


###############################################################################
# ImageField

# If Pillow available, do these tests.
if Image:
    class TestImageFieldFile(ImageFieldFile):
        """
        Custom Field File class that records whether or not the underlying file
        was opened.
        """
        def __init__(self, *args, **kwargs):
            self.was_opened = False
            super().__init__(*args, **kwargs)

        def open(self):
            self.was_opened = True
            super().open()

    class TestImageField(ImageField):
        attr_class = TestImageFieldFile

    # Set up a temp directory for file storage.
    temp_storage_dir = tempfile.mkdtemp()
    temp_storage = FileSystemStorage(temp_storage_dir)
    temp_upload_to_dir = os.path.join(temp_storage.location, 'tests')

    class Person(models.Model):
        """
        Model that defines an ImageField with no dimension fields.
        """
        name = models.CharField(max_length=50)
        mugshot = TestImageField(storage=temp_storage, upload_to='tests')

    class AbstractPersonWithHeight(models.Model):
        """
        Abstract model that defines an ImageField with only one dimension field
        to make sure the dimension update is correctly run on concrete subclass
        instance post-initialization.
        """
        mugshot = TestImageField(storage=temp_storage, upload_to='tests',
                                 height_field='mugshot_height')
        mugshot_height = models.PositiveSmallIntegerField()

        class Meta:
            abstract = True

    class PersonWithHeight(AbstractPersonWithHeight):
        """
        Concrete model that subclass an abstract one with only on dimension
        field.
        """
        name = models.CharField(max_length=50)

    class PersonWithHeightAndWidth(models.Model):
        """
        Model that defines height and width fields after the ImageField.
        """
        name = models.CharField(max_length=50)
        mugshot = TestImageField(storage=temp_storage, upload_to='tests',
                                 height_field='mugshot_height',
                                 width_field='mugshot_width')
        mugshot_height = models.PositiveSmallIntegerField()
        mugshot_width = models.PositiveSmallIntegerField()

    class PersonDimensionsFirst(models.Model):
        """
        Model that defines height and width fields before the ImageField.
        """
        name = models.CharField(max_length=50)
        mugshot_height = models.PositiveSmallIntegerField()
        mugshot_width = models.PositiveSmallIntegerField()
        mugshot = TestImageField(storage=temp_storage, upload_to='tests',
                                 height_field='mugshot_height',
                                 width_field='mugshot_width')

    class PersonTwoImages(models.Model):
        """
        Model that:
        * Defines two ImageFields
        * Defines the height/width fields before the ImageFields
        * Has a nullable ImageField
        """
        name = models.CharField(max_length=50)
        mugshot_height = models.PositiveSmallIntegerField()
        mugshot_width = models.PositiveSmallIntegerField()
        mugshot = TestImageField(storage=temp_storage, upload_to='tests',
                                 height_field='mugshot_height',
                                 width_field='mugshot_width')
        headshot_height = models.PositiveSmallIntegerField(
            blank=True, null=True)
        headshot_width = models.PositiveSmallIntegerField(
            blank=True, null=True)
        headshot = TestImageField(blank=True, null=True,
                                  storage=temp_storage, upload_to='tests',
                                  height_field='headshot_height',
                                  width_field='headshot_width')


class AllFieldsModel(models.Model):
    big_integer = models.BigIntegerField()
    binary = models.BinaryField()
    boolean = models.BooleanField(default=False)
    char = models.CharField(max_length=10)
    date = models.DateField()
    datetime = models.DateTimeField()
    decimal = models.DecimalField(decimal_places=2, max_digits=2)
    duration = models.DurationField()
    email = models.EmailField()
    file_path = models.FilePathField()
    floatf = models.FloatField()
    integer = models.IntegerField()
    generic_ip = models.GenericIPAddressField()
    null_boolean = models.NullBooleanField()
    positive_integer = models.PositiveIntegerField()
    positive_small_integer = models.PositiveSmallIntegerField()
    slug = models.SlugField()
    small_integer = models.SmallIntegerField()
    text = models.TextField()
    time = models.TimeField()
    url = models.URLField()
    uuid = models.UUIDField()

    fo = ForeignObject(
        'self',
        on_delete=models.CASCADE,
        from_fields=['abstract_non_concrete_id'],
        to_fields=['id'],
        related_name='reverse'
    )
    fk = ForeignKey(
        'self',
        models.CASCADE,
        related_name='reverse2'
    )
    m2m = ManyToManyField('self')
    oto = OneToOneField('self', models.CASCADE)

    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, models.CASCADE)
    gfk = GenericForeignKey()
    gr = GenericRelation(DataModel)


class ManyToMany(models.Model):
    m2m = models.ManyToManyField('self')


###############################################################################


class UUIDModel(models.Model):
    field = models.UUIDField()


class NullableUUIDModel(models.Model):
    field = models.UUIDField(blank=True, null=True)


class PrimaryKeyUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)


class RelatedToUUIDModel(models.Model):
    uuid_fk = models.ForeignKey('PrimaryKeyUUIDModel', models.CASCADE)


class UUIDChild(PrimaryKeyUUIDModel):
    pass


class UUIDGrandchild(UUIDChild):
    pass
