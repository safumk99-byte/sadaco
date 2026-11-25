from django.db import migrations


def install_staff_role_scope_guard(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        invalid = """
            NEW.department_id IS NOT NULL
            AND NEW.division_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM core_department d
                WHERE d.id = NEW.department_id
                  AND d.division_id = NEW.division_id
            )
        """
        schema_editor.execute(
            "CREATE TRIGGER core_staffrole_scope_insert "
            "BEFORE INSERT ON core_staffrole "
            f"WHEN {invalid} "
            "BEGIN SELECT RAISE(ABORT, 'Staff role department must belong to its division'); END"
        )
        schema_editor.execute(
            "CREATE TRIGGER core_staffrole_scope_update "
            "BEFORE UPDATE OF division_id, department_id ON core_staffrole "
            f"WHEN {invalid} "
            "BEGIN SELECT RAISE(ABORT, 'Staff role department must belong to its division'); END"
        )
    elif vendor == "postgresql":
        schema_editor.execute("""
            CREATE OR REPLACE FUNCTION core_guard_staffrole_scope()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.department_id IS NOT NULL
                   AND NEW.division_id IS NOT NULL
                   AND NOT EXISTS (
                       SELECT 1 FROM core_department d
                       WHERE d.id = NEW.department_id
                         AND d.division_id = NEW.division_id
                   ) THEN
                    RAISE EXCEPTION 'Staff role department must belong to its division';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        schema_editor.execute(
            "CREATE TRIGGER core_staffrole_scope_guard "
            "BEFORE INSERT OR UPDATE OF division_id, department_id ON core_staffrole "
            "FOR EACH ROW EXECUTE FUNCTION core_guard_staffrole_scope()"
        )


def remove_staff_role_scope_guard(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        schema_editor.execute("DROP TRIGGER IF EXISTS core_staffrole_scope_insert")
        schema_editor.execute("DROP TRIGGER IF EXISTS core_staffrole_scope_update")
    elif vendor == "postgresql":
        schema_editor.execute(
            "DROP TRIGGER IF EXISTS core_staffrole_scope_guard ON core_staffrole"
        )
        schema_editor.execute("DROP FUNCTION IF EXISTS core_guard_staffrole_scope()")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0012_order_task_actor_scope_guards"),
    ]

    operations = [
        migrations.RunPython(
            install_staff_role_scope_guard,
            reverse_code=remove_staff_role_scope_guard,
        ),
    ]
