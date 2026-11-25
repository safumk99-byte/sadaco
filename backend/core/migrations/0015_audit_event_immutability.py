from django.db import migrations


def install_audit_event_immutability(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        schema_editor.execute(
            "CREATE TRIGGER core_auditevent_no_update "
            "BEFORE UPDATE ON core_auditevent "
            "BEGIN SELECT RAISE(ABORT, 'Audit events are immutable'); END"
        )
        schema_editor.execute(
            "CREATE TRIGGER core_auditevent_no_delete "
            "BEFORE DELETE ON core_auditevent "
            "BEGIN SELECT RAISE(ABORT, 'Audit events cannot be deleted'); END"
        )
    elif vendor == "postgresql":
        schema_editor.execute("""
            CREATE OR REPLACE FUNCTION core_prevent_auditevent_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'Audit events are immutable and cannot be deleted';
            END;
            $$ LANGUAGE plpgsql;
        """)
        schema_editor.execute(
            "CREATE TRIGGER core_auditevent_immutable "
            "BEFORE UPDATE OR DELETE ON core_auditevent "
            "FOR EACH ROW EXECUTE FUNCTION core_prevent_auditevent_mutation()"
        )


def remove_audit_event_immutability(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        schema_editor.execute("DROP TRIGGER IF EXISTS core_auditevent_no_update")
        schema_editor.execute("DROP TRIGGER IF EXISTS core_auditevent_no_delete")
    elif vendor == "postgresql":
        schema_editor.execute(
            "DROP TRIGGER IF EXISTS core_auditevent_immutable ON core_auditevent"
        )
        schema_editor.execute(
            "DROP FUNCTION IF EXISTS core_prevent_auditevent_mutation()"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0014_design_approval_actor_scope_guard"),
    ]

    operations = [
        migrations.RunPython(
            install_audit_event_immutability,
            reverse_code=remove_audit_event_immutability,
        ),
    ]
