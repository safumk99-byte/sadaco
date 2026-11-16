from django.db import migrations


STAGES = (
    "design",
    "laser",
    "cnc",
    "assembly_sticking",
    "polishing_painting",
    "electrical_led",
    "final_assembly",
    "packing_installation",
)


def create_existing_job_stage_tasks(apps, schema_editor):
    ProductionJob = apps.get_model("production", "ProductionJob")
    ProductionStageTask = apps.get_model("production", "ProductionStageTask")
    db_alias = schema_editor.connection.alias
    batch = []
    for job_id in ProductionJob.objects.using(db_alias).values_list("pk", flat=True).iterator():
        for stage in STAGES:
            batch.append(ProductionStageTask(job_id=job_id, stage=stage))
        if len(batch) >= 2000:
            ProductionStageTask.objects.using(db_alias).bulk_create(batch, ignore_conflicts=True)
            batch = []
    if batch:
        ProductionStageTask.objects.using(db_alias).bulk_create(batch, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ("production", "0004_productionstagetask"),
    ]

    operations = [
        migrations.RunPython(create_existing_job_stage_tasks, migrations.RunPython.noop),
    ]
