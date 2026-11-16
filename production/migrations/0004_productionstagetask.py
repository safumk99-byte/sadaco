from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("production", "0003_production_cost_entries"),
        ("staff", "0002_staffprofile_department"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductionStageTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stage", models.CharField(choices=[("design", "Design"), ("laser", "Acrylic Laser Cutting"), ("cnc", "Wood CNC Cutting"), ("assembly_sticking", "Assembly / Sticking"), ("polishing_painting", "Polishing / Painting"), ("electrical_led", "Electrical / LED"), ("final_assembly", "Final Assembly"), ("packing_installation", "Packing / Installation")], max_length=30)),
                ("planned_start", models.DateField(blank=True, null=True)),
                ("expected_completion", models.DateField(blank=True, null=True)),
                ("actual_start", models.DateTimeField(blank=True, null=True)),
                ("actual_completion", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("assigned", "Assigned"), ("in_progress", "In Progress"), ("on_hold", "On Hold"), ("completed", "Completed"), ("skipped", "Skipped")], default="pending", max_length=20)),
                ("remarks", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_staff", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="production_stage_tasks", to="staff.staffprofile")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stage_tasks", to="production.productionjob")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_production_stage_tasks", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddConstraint(
            model_name="productionstagetask",
            constraint=models.UniqueConstraint(fields=("job", "stage"), name="prod_job_stage_task_unique"),
        ),
        migrations.AddIndex(
            model_name="productionstagetask",
            index=models.Index(fields=["assigned_staff", "status"], name="prod_stage_staff_status_idx"),
        ),
        migrations.AddIndex(
            model_name="productionstagetask",
            index=models.Index(fields=["status", "expected_completion"], name="prod_stage_status_due_idx"),
        ),
    ]
