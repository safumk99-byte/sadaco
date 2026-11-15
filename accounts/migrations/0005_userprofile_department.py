from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_push_subscription"),
        ("core", "0002_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="department",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="user_profiles", to="core.department",
            ),
        ),
    ]
