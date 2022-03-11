from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("unspecified_app_with_conflict", "0001_initial")]

    operations = [

        migrations.DeleteModel("Tribble"),

        migrations.RemoveField("Author", "silly_field"),

        migrations.AddField("Author", "rating", models.IntegerField(default=0)),

        migrations.CreateModel(
            "Book",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        )

    ]
