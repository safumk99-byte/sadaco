from django.db import migrations


def install_order_task_scope_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        actor_invalid = """
            NOT EXISTS (
                SELECT 1 FROM core_staffdivision sd
                JOIN core_salesorder so ON so.division_id = sd.division_id
                WHERE sd.staff_id = NEW.changed_by_id
                  AND so.id = NEW.sales_order_id
            )
            AND NOT EXISTS (
                SELECT 1 FROM core_staffrole sr
                JOIN core_role r ON r.id = sr.role_id
                JOIN core_salesorder so ON so.id = NEW.sales_order_id
                WHERE sr.staff_id = NEW.changed_by_id
                  AND r.code IN ('founder', 'super_admin')
                  AND sr.division_id IS NULL AND sr.department_id IS NULL
                  AND datetime(sr.valid_from) <= CURRENT_TIMESTAMP
                  AND (sr.valid_until IS NULL OR datetime(sr.valid_until) > CURRENT_TIMESTAMP)
            )
        """
        reporter_invalid = """
            NOT EXISTS (
                SELECT 1 FROM core_staffdivision sd
                JOIN core_stafftask st ON st.division_id = sd.division_id
                WHERE sd.staff_id = NEW.reported_by_id
                  AND st.id = NEW.staff_task_id
            )
        """
        for table, base, invalid, columns in [
            ("core_orderstatusevent", "core_order_event_scope", actor_invalid,
             "sales_order_id, changed_by_id"),
            ("core_taskupdate", "core_task_update_scope", reporter_invalid,
             "staff_task_id, reported_by_id"),
        ]:
            schema_editor.execute(
                f"CREATE TRIGGER {base}_insert BEFORE INSERT ON {table} "
                f"WHEN {invalid} BEGIN SELECT RAISE(ABORT, 'Order/task actor division scope is invalid'); END"
            )
            schema_editor.execute(
                f"CREATE TRIGGER {base}_update BEFORE UPDATE OF {columns} ON {table} "
                f"WHEN {invalid} BEGIN SELECT RAISE(ABORT, 'Order/task actor division scope is invalid'); END"
            )
    elif vendor == "postgresql":
        schema_editor.execute("""
            CREATE OR REPLACE FUNCTION core_guard_order_task_scope()
            RETURNS trigger AS $$
            BEGIN
                IF TG_TABLE_NAME = 'core_orderstatusevent' THEN
                    IF NOT EXISTS (
                        SELECT 1 FROM core_staffdivision sd
                        JOIN core_salesorder so ON so.division_id = sd.division_id
                        WHERE sd.staff_id = NEW.changed_by_id AND so.id = NEW.sales_order_id
                    ) AND NOT EXISTS (
                        SELECT 1 FROM core_staffrole sr
                        JOIN core_role r ON r.id = sr.role_id
                        JOIN core_salesorder so ON so.id = NEW.sales_order_id
                        WHERE sr.staff_id = NEW.changed_by_id
                          AND r.code IN ('founder', 'super_admin')
                          AND sr.division_id IS NULL AND sr.department_id IS NULL
                          AND sr.valid_from <= clock_timestamp()
                          AND (sr.valid_until IS NULL OR sr.valid_until > clock_timestamp())
                    ) THEN
                        RAISE EXCEPTION 'Order status actor division scope is invalid';
                    END IF;
                ELSIF TG_TABLE_NAME = 'core_taskupdate' THEN
                    IF NOT EXISTS (
                        SELECT 1 FROM core_staffdivision sd
                        JOIN core_stafftask st ON st.division_id = sd.division_id
                        WHERE sd.staff_id = NEW.reported_by_id AND st.id = NEW.staff_task_id
                    ) THEN
                        RAISE EXCEPTION 'Task update reporter division scope is invalid';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        for table, base, columns in [
            ("core_orderstatusevent", "core_order_event_scope",
             "sales_order_id, changed_by_id"),
            ("core_taskupdate", "core_task_update_scope",
             "staff_task_id, reported_by_id"),
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {base}_insert ON {table}")
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {base}_update ON {table}")
            schema_editor.execute(
                f"CREATE TRIGGER {base}_insert BEFORE INSERT ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION core_guard_order_task_scope()"
            )
            schema_editor.execute(
                f"CREATE TRIGGER {base}_update BEFORE UPDATE OF {columns} ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION core_guard_order_task_scope()"
            )


def remove_order_task_scope_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        for name in [
            "core_order_event_scope_insert", "core_order_event_scope_update",
            "core_task_update_scope_insert", "core_task_update_scope_update",
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {name}")
    elif vendor == "postgresql":
        for table, base in [
            ("core_orderstatusevent", "core_order_event_scope"),
            ("core_taskupdate", "core_task_update_scope"),
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {base}_insert ON {table}")
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {base}_update ON {table}")
        schema_editor.execute("DROP FUNCTION IF EXISTS core_guard_order_task_scope()")


class Migration(migrations.Migration):
    dependencies = [("core", "0011_crm_relationship_scope_guards")]
    operations = [
        migrations.RunPython(
            install_order_task_scope_guards,
            reverse_code=remove_order_task_scope_guards,
        ),
    ]
