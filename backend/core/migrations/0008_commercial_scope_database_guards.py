from django.db import migrations


def install_commercial_scope_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        guards = [
            (
                "core_quotation",
                "core_quotation_scope_insert",
                "core_quotation_scope_update",
                """
                (NEW.enquiry_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM core_enquiry e
                    WHERE e.id = NEW.enquiry_id
                      AND e.division_id = NEW.division_id
                      AND e.customer_id = NEW.customer_id
                ))
                OR NOT EXISTS (
                    SELECT 1 FROM core_staffdivision sd
                    WHERE sd.staff_id = NEW.prepared_by_id
                      AND sd.division_id = NEW.division_id
                )
                OR (NEW.approved_by_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM core_staffdivision sd
                    WHERE sd.staff_id = NEW.approved_by_id
                      AND sd.division_id = NEW.division_id
                ))
                """,
                "division_id, customer_id, enquiry_id, prepared_by_id, approved_by_id",
            ),
            (
                "core_salesorder",
                "core_salesorder_scope_insert",
                "core_salesorder_scope_update",
                """
                (NEW.quotation_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM core_quotation q
                    WHERE q.id = NEW.quotation_id
                      AND q.division_id = NEW.division_id
                      AND q.customer_id = NEW.customer_id
                ))
                OR NOT EXISTS (
                    SELECT 1 FROM core_staffdivision sd
                    WHERE sd.staff_id = NEW.created_by_id
                      AND sd.division_id = NEW.division_id
                )
                """,
                "division_id, customer_id, quotation_id, created_by_id",
            ),
        ]
        for table, insert_name, update_name, invalid, columns in guards:
            schema_editor.execute(
                f"CREATE TRIGGER IF NOT EXISTS {insert_name} BEFORE INSERT ON {table} "
                f"WHEN {invalid} BEGIN SELECT RAISE(ABORT, 'Quotation or sales order division relationship is invalid'); END"
            )
            schema_editor.execute(
                f"CREATE TRIGGER IF NOT EXISTS {update_name} BEFORE UPDATE OF {columns} ON {table} "
                f"WHEN {invalid} BEGIN SELECT RAISE(ABORT, 'Quotation or sales order division relationship is invalid'); END"
            )
    elif vendor == "postgresql":
        schema_editor.execute(
            """
            CREATE OR REPLACE FUNCTION core_guard_commercial_scope()
            RETURNS trigger AS $$
            BEGIN
                IF TG_TABLE_NAME = 'core_quotation' THEN
                    IF (NEW.enquiry_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_enquiry e
                        WHERE e.id = NEW.enquiry_id
                          AND e.division_id = NEW.division_id
                          AND e.customer_id = NEW.customer_id
                    )) OR NOT EXISTS (
                        SELECT 1 FROM core_staffdivision sd
                        WHERE sd.staff_id = NEW.prepared_by_id
                          AND sd.division_id = NEW.division_id
                    ) OR (NEW.approved_by_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_staffdivision sd
                        WHERE sd.staff_id = NEW.approved_by_id
                          AND sd.division_id = NEW.division_id
                    )) THEN
                        RAISE EXCEPTION 'Quotation division, enquiry, customer, or staff relationship is invalid';
                    END IF;
                ELSIF TG_TABLE_NAME = 'core_salesorder' THEN
                    IF (NEW.quotation_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_quotation q
                        WHERE q.id = NEW.quotation_id
                          AND q.division_id = NEW.division_id
                          AND q.customer_id = NEW.customer_id
                    )) OR NOT EXISTS (
                        SELECT 1 FROM core_staffdivision sd
                        WHERE sd.staff_id = NEW.created_by_id
                          AND sd.division_id = NEW.division_id
                    ) THEN
                        RAISE EXCEPTION 'Sales order division, quotation, customer, or creator relationship is invalid';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        for table, trigger, columns in [
            ("core_quotation", "core_quotation_scope_guard", "division_id, customer_id, enquiry_id, prepared_by_id, approved_by_id"),
            ("core_salesorder", "core_salesorder_scope_guard", "division_id, customer_id, quotation_id, created_by_id"),
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
            schema_editor.execute(
                f"CREATE TRIGGER {trigger} BEFORE INSERT OR UPDATE OF {columns} ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION core_guard_commercial_scope()"
            )


def remove_commercial_scope_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        for trigger in [
            "core_quotation_scope_insert", "core_quotation_scope_update",
            "core_salesorder_scope_insert", "core_salesorder_scope_update",
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger}")
    elif vendor == "postgresql":
        for table, trigger in [
            ("core_quotation", "core_quotation_scope_guard"),
            ("core_salesorder", "core_salesorder_scope_guard"),
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
        schema_editor.execute("DROP FUNCTION IF EXISTS core_guard_commercial_scope()")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_division_assignment_database_guards"),
    ]

    operations = [
        migrations.RunPython(
            install_commercial_scope_guards,
            reverse_code=remove_commercial_scope_guards,
        ),
    ]
