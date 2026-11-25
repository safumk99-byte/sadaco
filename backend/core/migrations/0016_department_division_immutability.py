from django.db import migrations


def install_department_division_immutability(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        invalid = """
            EXISTS (
                SELECT 1 FROM core_staffrole sr
                WHERE sr.department_id = OLD.id
            )
            OR EXISTS (
                SELECT 1 FROM core_staffdepartment sd
                WHERE sd.department_id = OLD.id
            )
        """
        schema_editor.execute(
            "CREATE TRIGGER core_department_division_immutable "
            "BEFORE UPDATE OF division_id ON core_department "
            f"WHEN NEW.division_id <> OLD.division_id AND ({invalid}) "
            "BEGIN SELECT RAISE(ABORT, 'Department division cannot change while staff role or membership links exist'); END"
        )
    elif vendor == "postgresql":
        schema_editor.execute("""
            CREATE OR REPLACE FUNCTION core_guard_department_division_change()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.division_id IS DISTINCT FROM OLD.division_id
                   AND (
                       EXISTS (
                           SELECT 1 FROM core_staffrole sr
                           WHERE sr.department_id = OLD.id
                       )
                       OR EXISTS (
                           SELECT 1 FROM core_staffdepartment sd
                           WHERE sd.department_id = OLD.id
                       )
                   ) THEN
                    RAISE EXCEPTION 'Department division cannot change while staff role or membership links exist';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        schema_editor.execute(
            "CREATE TRIGGER core_department_division_immutable "
            "BEFORE UPDATE OF division_id ON core_department "
            "FOR EACH ROW EXECUTE FUNCTION core_guard_department_division_change()"
        )


def remove_department_division_immutability(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        schema_editor.execute(
            "DROP TRIGGER IF EXISTS core_department_division_immutable"
        )
    elif vendor == "postgresql":
        schema_editor.execute(
            "DROP TRIGGER IF EXISTS core_department_division_immutable ON core_department"
        )
        schema_editor.execute(
            "DROP FUNCTION IF EXISTS core_guard_department_division_change()"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0015_audit_event_immutability"),
    ]

    operations = [
        migrations.RunPython(
            install_department_division_immutability,
            reverse_code=remove_department_division_immutability,
        ),
    ]
