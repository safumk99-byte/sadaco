from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0010_quotation_catalogue_product"),
    ]

    operations = [
        migrations.CreateModel(
            name="SalesOrderSequence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveSmallIntegerField(unique=True)),
                ("last_number", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["year"]},
        ),
    ]
