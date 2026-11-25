from django.db import migrations


def install_design_approval_guards(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor
    table = connection.ops.quote_name("core_designapproval")

    if vendor == "sqlite":
        schema_editor.execute(
            f'CREATE TRIGGER IF NOT EXISTS core_designapproval_no_update '
            f'BEFORE UPDATE ON {table} BEGIN '
            "SELECT RAISE(ABORT, 'Design approval history is immutable'); END"
        )
        schema_editor.execute(
            f'CREATE TRIGGER IF NOT EXISTS core_designapproval_no_delete '
            f'BEFORE DELETE ON {table} BEGIN '
            "SELECT RAISE(ABORT, 'Design approval history cannot be deleted'); END"
        )
    elif vendor == "postgresql":
        schema_editor.execute(
            """
            CREATE OR REPLACE FUNCTION core_prevent_designapproval_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'Design approval history is immutable';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        schema_editor.execute(
            f'DROP TRIGGER IF EXISTS core_designapproval_immutable ON {table}'
        )
        schema_editor.execute(
            f'CREATE TRIGGER core_designapproval_immutable '
            f'BEFORE UPDATE OR DELETE ON {table} '
            'FOR EACH ROW EXECUTE FUNCTION core_prevent_designapproval_mutation()'
        )


def remove_design_approval_guards(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor
    table = connection.ops.quote_name("core_designapproval")

    if vendor == "sqlite":
        schema_editor.execute("DROP TRIGGER IF EXISTS core_designapproval_no_update")
        schema_editor.execute("DROP TRIGGER IF EXISTS core_designapproval_no_delete")
    elif vendor == "postgresql":
        schema_editor.execute(
            f'DROP TRIGGER IF EXISTS core_designapproval_immutable ON {table}'
        )
        schema_editor.execute(
            "DROP FUNCTION IF EXISTS core_prevent_designapproval_mutation()"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_remove_staffrole_uq_active_staff_role_scope_and_more"),
    ]

    operations = [
        migrations.RunPython(
            install_design_approval_guards,
            reverse_code=remove_design_approval_guards,
        ),
    ]
