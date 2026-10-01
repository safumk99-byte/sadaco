from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("production", "0001_initial"),
        ("staff", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="QualityCheck",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("check_type", models.CharField(choices=[("station","Station QC"),("final","Final QC")], max_length=20)),
                ("result", models.CharField(choices=[("pending","Pending"),("pass","Passed"),("fail","Failed"),("rework","Rework Required")], default="pending", max_length=20)),
                ("stage", models.CharField(blank=True, max_length=30)),
                ("design_match", models.BooleanField(default=False)),
                ("measurement_ok", models.BooleanField(default=False)),
                ("finishing_ok", models.BooleanField(default=False)),
                ("colour_ok", models.BooleanField(default=False)),
                ("engraving_ok", models.BooleanField(default=False)),
                ("defects", models.TextField(blank=True)),
                ("rework_reason", models.TextField(blank=True)),
                ("corrective_action", models.TextField(blank=True)),
                ("rework_count", models.PositiveSmallIntegerField(default=0)),
                ("remarks", models.TextField(blank=True)),
                ("checked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_quality_checks", to=settings.AUTH_USER_MODEL)),
                ("inspector", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="quality_checks", to="staff.staffprofile")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="quality_checks", to="production.productionjob")),
            ],
            options={"ordering":["-created_at"],"indexes":[
                models.Index(fields=["job","result"], name="quality_qual_job_id_9c6a3f_idx"),
                models.Index(fields=["check_type","result"], name="quality_qual_check_t_0c4c1e_idx"),
            ]},
        ),
        migrations.CreateModel(
            name="ReworkRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.TextField()),
                ("corrective_action", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("open","Open"),("in_progress","In Progress"),("completed","Completed"),("cancelled","Cancelled")], default="open", max_length=20)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_staff", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="quality_rework_assignments", to="staff.staffprofile")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_rework_records", to=settings.AUTH_USER_MODEL)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rework_records", to="production.productionjob")),
                ("quality_check", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reworks", to="quality.qualitycheck")),
            ],
            options={"ordering":["status","-created_at"]},
        ),
        migrations.CreateModel(
            name="PackingRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("packing_material", models.CharField(blank=True, max_length=180)),
                ("fragile_protection", models.BooleanField(default=False)),
                ("customer_label", models.BooleanField(default=False)),
                ("status", models.CharField(choices=[("pending","Pending"),("packed","Packed")], default="pending", max_length=20)),
                ("packed_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("job", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="packing", to="production.productionjob")),
                ("packed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="packing_records", to="staff.staffprofile")),
            ],
        ),
    ]
