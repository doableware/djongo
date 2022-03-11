from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    operations = [
        migrations.CreateModel(
            "Author",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(null=True)),
                ("age", models.IntegerField(default=0)),
                ("silly_field", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            "Tribble",
            [
                ("id", models.AutoField(primary_key=True)),
                ("fluffy", models.BooleanField(default=True)),
            ],
        ),
        migrations.AddField(
            model_name='tribble',
            name='bool',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterUniqueTogether(
            name='author',
            unique_together={('name', 'slug')},
        ),
    ]
