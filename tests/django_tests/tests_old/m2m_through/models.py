from datetime import datetime

from django.db import models


# M2M described on one of the models
class Person(models.Model):
    name = models.CharField(max_length=128)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=128)
    members = models.ManyToManyField(Person, through='Membership')
    custom_members = models.ManyToManyField(Person, through='CustomMembership', related_name="custom")
    nodefaultsnonulls = models.ManyToManyField(
        Person,
        through='TestNoDefaultsOrNulls',
        related_name="testnodefaultsnonulls",
    )

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class Membership(models.Model):
    person = models.ForeignKey(Person, models.CASCADE)
    group = models.ForeignKey(Group, models.CASCADE)
    date_joined = models.DateTimeField(default=datetime.now)
    invite_reason = models.CharField(max_length=64, null=True)

    class Meta:
        ordering = ('date_joined', 'invite_reason', 'group')

    def __str__(self):
        return "%s is a member of %s" % (self.person.name, self.group.name)


class CustomMembership(models.Model):
    person = models.ForeignKey(
        Person,
        models.CASCADE,
        db_column="custom_person_column",
        related_name="custom_person_related_name",
    )
    group = models.ForeignKey(Group, models.CASCADE)
    weird_fk = models.ForeignKey(Membership, models.SET_NULL, null=True)
    date_joined = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return "%s is a member of %s" % (self.person.name, self.group.name)

    class Meta:
        db_table = "test_table"
        ordering = ["date_joined"]


class TestNoDefaultsOrNulls(models.Model):
    person = models.ForeignKey(Person, models.CASCADE)
    group = models.ForeignKey(Group, models.CASCADE)
    nodefaultnonull = models.CharField(max_length=5)


class PersonSelfRefM2M(models.Model):
    name = models.CharField(max_length=5)
    friends = models.ManyToManyField('self', through="Friendship", symmetrical=False)

    def __str__(self):
        return self.name


class Friendship(models.Model):
    first = models.ForeignKey(PersonSelfRefM2M, models.CASCADE, related_name="rel_from_set")
    second = models.ForeignKey(PersonSelfRefM2M, models.CASCADE, related_name="rel_to_set")
    date_friended = models.DateTimeField()


# Custom through link fields
class Event(models.Model):
    title = models.CharField(max_length=50)
    invitees = models.ManyToManyField(
        Person, through='Invitation',
        through_fields=('event', 'invitee'),
        related_name='events_invited',
    )

    def __str__(self):
        return self.title


class Invitation(models.Model):
    event = models.ForeignKey(Event, models.CASCADE, related_name='invitations')
    # field order is deliberately inverted. the target field is "invitee".
    inviter = models.ForeignKey(Person, models.CASCADE, related_name='invitations_sent')
    invitee = models.ForeignKey(Person, models.CASCADE, related_name='invitations')


class Employee(models.Model):
    name = models.CharField(max_length=5)
    subordinates = models.ManyToManyField(
        'self',
        through="Relationship",
        through_fields=('source', 'target'),
        symmetrical=False,
    )

    class Meta:
        ordering = ('pk',)

    def __str__(self):
        return self.name


class Relationship(models.Model):
    # field order is deliberately inverted.
    another = models.ForeignKey(Employee, models.SET_NULL, related_name="rel_another_set", null=True)
    target = models.ForeignKey(Employee, models.CASCADE, related_name="rel_target_set")
    source = models.ForeignKey(Employee, models.CASCADE, related_name="rel_source_set")


class Ingredient(models.Model):
    iname = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ('iname',)


class Recipe(models.Model):
    rname = models.CharField(max_length=20, unique=True)
    ingredients = models.ManyToManyField(
        Ingredient, through='RecipeIngredient', related_name='recipes',
    )

    class Meta:
        ordering = ('rname',)


class RecipeIngredient(models.Model):
    ingredient = models.ForeignKey(Ingredient, models.CASCADE, to_field='iname')
    recipe = models.ForeignKey(Recipe, models.CASCADE, to_field='rname')
