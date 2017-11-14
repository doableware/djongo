from djongo import models

# Create your models here.

class Embedded(models.Model):
    text = models.CharField(max_length=100)

    class Meta:
        abstract = True


class Dummy(models.Model):

    test = models.CharField(max_length=10)
    embedded = models.EmbeddedModelField(model_container=Embedded)

class Dummy2(models.Model):

    test = models.CharField(max_length=10)
    embedded = models.EmbeddedModelField(model_container=Embedded)

class DummyForm(models.forms.ModelForm):
    class Meta:
        model = Embedded
        fields = (
            'text',
        )


class Dummies(models.Model):
    h1 = models.CharField(max_length=100)
    content = models.ArrayModelField(
        model_container=Embedded,
        model_form=DummyForm
    )