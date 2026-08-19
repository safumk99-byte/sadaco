from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0004_link_requests_to_quotations"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerInteraction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("interaction_type", models.CharField(choices=[("call","Phone Call"),("whatsapp","WhatsApp"),("email","Email"),("meeting","Meeting"),("follow_up","Follow-up"),("note","Note")], default="note", max_length=20)),
                ("subject", models.CharField(max_length=180)),
                ("notes", models.TextField(blank=True)),
                ("next_follow_up", models.DateField(blank=True, null=True)),
                ("completed", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="customer_interactions_created", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interactions", to="sales.customer")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["customer", "-created_at"], name="sales_custint_customer_8c4e0a_idx"),
                    models.Index(fields=["next_follow_up", "completed"], name="sales_custint_follow_6f7b2d_idx"),
                ],
            },
        ),
    ]
