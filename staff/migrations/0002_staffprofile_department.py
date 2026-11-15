from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("staff", "0001_initial"),
        ("core", "0002_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffprofile",
            name="department",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="staff_members", to="core.department",
            ),
        ),
    ]
