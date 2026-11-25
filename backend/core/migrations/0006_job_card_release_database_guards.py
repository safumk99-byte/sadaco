from django.db import migrations


def install_job_card_guards(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor
    table = connection.ops.quote_name("core_jobcard")

    if vendor == "sqlite":
        invalid_reference = (
            "NOT EXISTS ("
            "SELECT 1 FROM core_designrevision r "
            "JOIN core_designrecord d ON d.id = r.design_record_id "
            "JOIN core_salesorder o ON o.id = NEW.sales_order_id "
            "WHERE r.id = NEW.approved_design_revision_id "
            "AND r.status = 'approved' AND r.locked_at IS NOT NULL "
            "AND d.sales_order_id = NEW.sales_order_id "
            "AND o.division_id = NEW.division_id)"
        )
        schema_editor.execute(
            f"CREATE TRIGGER IF NOT EXISTS core_jobcard_release_insert "
            f"BEFORE INSERT ON {table} WHEN {invalid_reference} "
            "BEGIN SELECT RAISE(ABORT, 'Job cards require a locked approved design revision for the same order and division'); END"
        )
        schema_editor.execute(
            f"CREATE TRIGGER IF NOT EXISTS core_jobcard_release_update "
            f"BEFORE UPDATE OF sales_order_id, approved_design_revision_id, division_id ON {table} "
            f"WHEN {invalid_reference} "
            "BEGIN SELECT RAISE(ABORT, 'Job cards require a locked approved design revision for the same order and division'); END"
        )
    elif vendor == "postgresql":
        schema_editor.execute(
            """
            CREATE OR REPLACE FUNCTION core_guard_jobcard_release()
            RETURNS trigger AS $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM core_designrevision r
                    JOIN core_designrecord d ON d.id = r.design_record_id
                    JOIN core_salesorder o ON o.id = NEW.sales_order_id
                    WHERE r.id = NEW.approved_design_revision_id
                      AND r.status = 'approved'
                      AND r.locked_at IS NOT NULL
                      AND d.sales_order_id = NEW.sales_order_id
                      AND o.division_id = NEW.division_id
                ) THEN
                    RAISE EXCEPTION 'Job cards require a locked approved design revision for the same order and division';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        schema_editor.execute(f"DROP TRIGGER IF EXISTS core_jobcard_release_guard ON {table}")
        schema_editor.execute(
            f"CREATE TRIGGER core_jobcard_release_guard "
            f"BEFORE INSERT OR UPDATE OF sales_order_id, approved_design_revision_id, division_id ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION core_guard_jobcard_release()"
        )


def remove_job_card_guards(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor == "sqlite":
        schema_editor.execute("DROP TRIGGER IF EXISTS core_jobcard_release_insert")
        schema_editor.execute("DROP TRIGGER IF EXISTS core_jobcard_release_update")
    elif connection.vendor == "postgresql":
        schema_editor.execute(
            f"DROP TRIGGER IF EXISTS core_jobcard_release_guard ON {connection.ops.quote_name('core_jobcard')}"
        )
        schema_editor.execute("DROP FUNCTION IF EXISTS core_guard_jobcard_release()")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_design_revision_database_guards"),
    ]

    operations = [
        migrations.RunPython(
            install_job_card_guards,
            reverse_code=remove_job_card_guards,
        ),
    ]
