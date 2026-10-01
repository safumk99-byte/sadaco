from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ApprovalRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("module", models.CharField(max_length=60)),
                ("action", models.CharField(max_length=120)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("reason", models.TextField()),
                ("status", models.CharField(choices=[("pending","Pending"),("approved","Approved"),("rejected","Rejected"),("cancelled","Cancelled")], default="pending", max_length=20)),
                ("reviewer_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("requested_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approval_requests_created", to=settings.AUTH_USER_MODEL)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approval_requests_reviewed", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"], "indexes": [
                models.Index(fields=["status","created_at"], name="core_approv_status_5d3f0a_idx"),
                models.Index(fields=["module","status"], name="core_approv_module_9c2b12_idx"),
            ]},
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("module", models.CharField(max_length=60)),
                ("action", models.CharField(choices=[("create","Created"),("update","Updated"),("delete","Deleted"),("approve","Approved"),("reject","Rejected"),("login","Login"),("other","Other")], default="other", max_length=20)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("description", models.TextField(blank=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"], "indexes": [
                models.Index(fields=["module","created_at"], name="core_audit_module_3f7a2a_idx"),
                models.Index(fields=["user","created_at"], name="core_audit_user_7c1e11_idx"),
            ]},
        ),
    ]
