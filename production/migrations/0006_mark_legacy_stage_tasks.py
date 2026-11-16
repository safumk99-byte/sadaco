from django.db import migrations


LEGACY_NOTE = (
    "Legacy production job predates stage-level tracking; individual stage "
    "completion was not recorded before this feature was introduced."
)


def mark_legacy_stage_tasks(apps, schema_editor):
    ProductionStageTask = apps.get_model("production", "ProductionStageTask")
    db_alias = schema_editor.connection.alias
    ProductionStageTask.objects.using(db_alias).filter(
        status="pending",
        remarks="",
    ).update(
        status="skipped",
        remarks=LEGACY_NOTE,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("production", "0005_seed_existing_production_stage_tasks"),
    ]

    operations = [
        migrations.RunPython(mark_legacy_stage_tasks, migrations.RunPython.noop),
    ]
