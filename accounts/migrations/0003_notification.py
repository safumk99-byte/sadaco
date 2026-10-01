from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_userprofile_permissions"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notification_type", models.CharField(choices=[("info","Information"),("order","Order"),("enquiry","Enquiry"),("stock","Stock Alert"),("task","Task"),("payment","Payment"),("system","System")], default="info", max_length=20)),
                ("priority", models.CharField(choices=[("low","Low"),("normal","Normal"),("high","High"),("urgent","Urgent")], default="normal", max_length=10)),
                ("title", models.CharField(max_length=180)),
                ("message", models.TextField(blank=True)),
                ("url", models.CharField(blank=True, max_length=255)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["user","is_read","created_at"], name="accounts_not_user_id_8d0d0e_idx"),
                    models.Index(fields=["user","created_at"], name="accounts_not_user_id_5cdb2d_idx"),
                ],
            },
        ),
    ]
