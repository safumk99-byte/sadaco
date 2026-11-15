from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_departments(apps, schema_editor):
    Department = apps.get_model("core", "Department")
    defaults = [
        ("creatives", "SADACO Creatives", "Creative design and branding division."),
        ("cnc", "SADACO CNC", "CNC cutting and manufacturing division."),
        ("decor", "SADACO Decor Co.", "Decor, furnishing and installation division."),
    ]
    for code, name, description in defaults:
        Department.objects.get_or_create(
            code=code,
            defaults={"name": name, "description": description, "is_active": True},
        )


def unseed_departments(apps, schema_editor):
    Department = apps.get_model("core", "Department")
    Department.objects.filter(code__in=["creatives", "cnc", "decor"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_audit_approval"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=40, unique=True)),
                ("name", models.CharField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("manager", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="managed_department", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["name"],
                "permissions": [("manage_departments", "Can manage SADACO departments")],
            },
        ),
        migrations.RunPython(seed_departments, unseed_departments),
    ]
