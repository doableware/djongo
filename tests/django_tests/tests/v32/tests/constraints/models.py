from django.db import models


class Product(models.Model):
    price = models.IntegerField(null=True)
    discounted_price = models.IntegerField(null=True)
    unit = models.CharField(max_length=15, null=True)

    class Meta:
        required_db_features = {
            'supports_table_check_constraints',
        }
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gt=models.F('discounted_price')),
                name='price_gt_discounted_price',
            ),
            models.CheckConstraint(
                check=models.Q(price__gt=0),
                name='%(app_label)s_%(class)s_price_gt_0',
            ),
            models.CheckConstraint(
                check=models.expressions.RawSQL(
                    'price < %s', (1000,), output_field=models.BooleanField()
                ),
                name='%(app_label)s_price_lt_1000_raw',
            ),
            models.CheckConstraint(
                check=models.expressions.ExpressionWrapper(
                    models.Q(price__gt=500) | models.Q(price__lt=500),
                    output_field=models.BooleanField()
                ),
                name='%(app_label)s_price_neq_500_wrap',
            ),
            models.CheckConstraint(
                check=models.Q(
                    models.Q(unit__isnull=True) |
                    models.Q(unit__in=['μg/mL', 'ng/mL'])
                ),
                name='unicode_unit_list',
            ),
        ]


class UniqueConstraintProduct(models.Model):
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=32, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'color'], name='name_color_uniq'),
        ]


class UniqueConstraintConditionProduct(models.Model):
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=32, null=True)

    class Meta:
        required_db_features = {'supports_partial_indexes'}
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                name='name_without_color_uniq',
                condition=models.Q(color__isnull=True),
            ),
        ]


class UniqueConstraintDeferrable(models.Model):
    name = models.CharField(max_length=255)
    shelf = models.CharField(max_length=31)

    class Meta:
        required_db_features = {
            'supports_deferrable_unique_constraints',
        }
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                name='name_init_deferred_uniq',
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.UniqueConstraint(
                fields=['shelf'],
                name='sheld_init_immediate_uniq',
                deferrable=models.Deferrable.IMMEDIATE,
            ),
        ]


class UniqueConstraintInclude(models.Model):
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=32, null=True)

    class Meta:
        required_db_features = {
            'supports_table_check_constraints',
            'supports_covering_indexes',
        }
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                name='name_include_color_uniq',
                include=['color'],
            ),
        ]


class AbstractModel(models.Model):
    age = models.IntegerField()

    class Meta:
        abstract = True
        required_db_features = {
            'supports_table_check_constraints',
        }
        constraints = [
            models.CheckConstraint(
                check=models.Q(age__gte=18),
                name='%(app_label)s_%(class)s_adult',
            ),
        ]


class ChildModel(AbstractModel):
    pass
