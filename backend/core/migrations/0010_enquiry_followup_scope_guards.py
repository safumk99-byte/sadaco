from django.db import migrations


def install_enquiry_followup_scope_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        enquiry_invalid = """
            (NEW.assigned_to_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM core_staffdivision sd
                WHERE sd.staff_id = NEW.assigned_to_id
                  AND sd.division_id = NEW.division_id
            ))
            OR (
                NOT EXISTS (
                    SELECT 1 FROM core_staffdivision sd
                    WHERE sd.staff_id = NEW.created_by_id
                      AND sd.division_id = NEW.division_id
                )
                AND NOT EXISTS (
                    SELECT 1 FROM core_staffrole sr
                    JOIN core_role r ON r.id = sr.role_id
                    WHERE sr.staff_id = NEW.created_by_id
                      AND r.code IN ('founder', 'super_admin')
                      AND sr.division_id IS NULL
                      AND sr.department_id IS NULL
                      AND datetime(sr.valid_from) <= CURRENT_TIMESTAMP
                      AND (sr.valid_until IS NULL OR datetime(sr.valid_until) > CURRENT_TIMESTAMP)
                )
            )
        """
        followup_invalid = """
            NEW.assigned_to_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM core_enquiry e
                JOIN core_staffdivision sd ON sd.division_id = e.division_id
                WHERE e.id = NEW.enquiry_id
                  AND sd.staff_id = NEW.assigned_to_id
            )
        """
        for table, base, invalid, columns in [
            ("core_enquiry", "core_enquiry_division_scope", enquiry_invalid,
             "division_id, assigned_to_id, created_by_id"),
            ("core_followup", "core_followup_division_scope", followup_invalid,
             "enquiry_id, assigned_to_id"),
        ]:
            schema_editor.execute(
                f"CREATE TRIGGER {base}_insert BEFORE INSERT ON {table} "
                f"WHEN {invalid} BEGIN SELECT RAISE(ABORT, 'Enquiry or follow-up division assignment is invalid'); END"
            )
            schema_editor.execute(
                f"CREATE TRIGGER {base}_update BEFORE UPDATE OF {columns} ON {table} "
                f"WHEN {invalid} BEGIN SELECT RAISE(ABORT, 'Enquiry or follow-up division assignment is invalid'); END"
            )
    elif vendor == "postgresql":
        schema_editor.execute("""
            CREATE OR REPLACE FUNCTION core_guard_enquiry_followup_scope()
            RETURNS trigger AS $$
            BEGIN
                IF TG_TABLE_NAME = 'core_enquiry' THEN
                    IF (NEW.assigned_to_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_staffdivision sd
                        WHERE sd.staff_id = NEW.assigned_to_id
                          AND sd.division_id = NEW.division_id
                    )) OR (
                        NOT EXISTS (
                            SELECT 1 FROM core_staffdivision sd
                            WHERE sd.staff_id = NEW.created_by_id
                              AND sd.division_id = NEW.division_id
                        )
                        AND NOT EXISTS (
                            SELECT 1 FROM core_staffrole sr
                            JOIN core_role r ON r.id = sr.role_id
                            WHERE sr.staff_id = NEW.created_by_id
                              AND r.code IN ('founder', 'super_admin')
                              AND sr.division_id IS NULL
                              AND sr.department_id IS NULL
                              AND sr.valid_from <= clock_timestamp()
                              AND (sr.valid_until IS NULL OR sr.valid_until > clock_timestamp())
                        )
                    ) THEN
                        RAISE EXCEPTION 'Enquiry assignee or creator division relationship is invalid';
                    END IF;
                ELSIF TG_TABLE_NAME = 'core_followup' THEN
                    IF NEW.assigned_to_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_enquiry e
                        JOIN core_staffdivision sd ON sd.division_id = e.division_id
                        WHERE e.id = NEW.enquiry_id
                          AND sd.staff_id = NEW.assigned_to_id
                    ) THEN
                        RAISE EXCEPTION 'Follow-up assignee must belong to the enquiry division';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        for table, base, columns in [
            ("core_enquiry", "core_enquiry_division_scope",
             "division_id, assigned_to_id, created_by_id"),
            ("core_followup", "core_followup_division_scope",
             "enquiry_id, assigned_to_id"),
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {base}_insert ON {table}")
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {base}_update ON {table}")
            schema_editor.execute(
                f"CREATE TRIGGER {base}_insert BEFORE INSERT ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION core_guard_enquiry_followup_scope()"
            )
            schema_editor.execute(
                f"CREATE TRIGGER {base}_update BEFORE UPDATE OF {columns} ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION core_guard_enquiry_followup_scope()"
            )


def remove_enquiry_followup_scope_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        for name in [
            "core_enquiry_division_scope_insert", "core_enquiry_division_scope_update",
            "core_followup_division_scope_insert", "core_followup_division_scope_update",
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {name}")
    elif vendor == "postgresql":
        for table, base in [
            ("core_enquiry", "core_enquiry_division_scope"),
            ("core_followup", "core_followup_division_scope"),
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {base}_insert ON {table}")
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {base}_update ON {table}")
        schema_editor.execute("DROP FUNCTION IF EXISTS core_guard_enquiry_followup_scope()")


class Migration(migrations.Migration):
    dependencies = [("core", "0009_global_founder_division_scope")]
    operations = [
        migrations.RunPython(
            install_enquiry_followup_scope_guards,
            reverse_code=remove_enquiry_followup_scope_guards,
        ),
    ]
