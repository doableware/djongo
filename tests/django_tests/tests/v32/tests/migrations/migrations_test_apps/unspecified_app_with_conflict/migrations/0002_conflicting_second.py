from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("unspecified_app_with_conflict", "0001_initial")]

    operations = [

        migrations.CreateModel(
            "Something",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        )

    ]
