from django.db import migrations


def install_crm_relationship_scope_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        communication_invalid = """
            (
                NEW.enquiry_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM core_enquiry e
                    WHERE e.id = NEW.enquiry_id
                      AND e.division_id = NEW.division_id
                      AND e.customer_id = NEW.customer_id
                )
            )
            OR NOT EXISTS (
                SELECT 1 FROM core_staffdivision sd
                WHERE sd.staff_id = NEW.recorded_by_id
                  AND sd.division_id = NEW.division_id
            )
            AND NOT EXISTS (
                SELECT 1 FROM core_staffrole sr
                JOIN core_role r ON r.id = sr.role_id
                WHERE sr.staff_id = NEW.recorded_by_id
                  AND r.code IN ('founder', 'super_admin')
                  AND sr.division_id IS NULL
                  AND sr.department_id IS NULL
                  AND datetime(sr.valid_from) <= CURRENT_TIMESTAMP
                  AND (sr.valid_until IS NULL OR datetime(sr.valid_until) > CURRENT_TIMESTAMP)
            )
        """
        approval_invalid = """
            (
                NOT EXISTS (
                    SELECT 1 FROM core_staffdivision sd
                    WHERE sd.staff_id = NEW.requested_by_id
                      AND sd.division_id = NEW.division_id
                )
                AND NOT EXISTS (
                    SELECT 1 FROM core_staffrole sr
                    JOIN core_role r ON r.id = sr.role_id
                    WHERE sr.staff_id = NEW.requested_by_id
                      AND r.code IN ('founder', 'super_admin')
                      AND sr.division_id IS NULL
                      AND sr.department_id IS NULL
                      AND datetime(sr.valid_from) <= CURRENT_TIMESTAMP
                      AND (sr.valid_until IS NULL OR datetime(sr.valid_until) > CURRENT_TIMESTAMP)
                )
            )
            OR (
                NEW.decided_by_id IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM core_staffdivision sd
                    WHERE sd.staff_id = NEW.decided_by_id
                      AND sd.division_id = NEW.division_id
                )
                AND NOT EXISTS (
                    SELECT 1 FROM core_staffrole sr
                    JOIN core_role r ON r.id = sr.role_id
                    WHERE sr.staff_id = NEW.decided_by_id
                      AND r.code IN ('founder', 'super_admin')
                      AND sr.division_id IS NULL
                      AND sr.department_id IS NULL
                      AND datetime(sr.valid_from) <= CURRENT_TIMESTAMP
                      AND (sr.valid_until IS NULL OR datetime(sr.valid_until) > CURRENT_TIMESTAMP)
                )
            )
        """
        for table, base, invalid, columns in [
            ("core_customercommunication", "core_communication_scope",
             communication_invalid, "customer_id, enquiry_id, division_id, recorded_by_id"),
            ("core_approvalrequest", "core_approval_request_scope",
             approval_invalid, "division_id, requested_by_id, decided_by_id"),
        ]:
            schema_editor.execute(
                f"CREATE TRIGGER {base}_insert BEFORE INSERT ON {table} "
                f"WHEN {invalid} BEGIN SELECT RAISE(ABORT, 'CRM relationship division scope is invalid'); END"
            )
            schema_editor.execute(
                f"CREATE TRIGGER {base}_update BEFORE UPDATE OF {columns} ON {table} "
                f"WHEN {invalid} BEGIN SELECT RAISE(ABORT, 'CRM relationship division scope is invalid'); END"
            )
    elif vendor == "postgresql":
        schema_editor.execute("""
            CREATE OR REPLACE FUNCTION core_guard_crm_relationship_scope()
            RETURNS trigger AS $$
            BEGIN
                IF TG_TABLE_NAME = 'core_customercommunication' THEN
                    IF (
                        NEW.enquiry_id IS NOT NULL AND NOT EXISTS (
                            SELECT 1 FROM core_enquiry e
                            WHERE e.id = NEW.enquiry_id
                              AND e.division_id = NEW.division_id
                              AND e.customer_id = NEW.customer_id
                        )
                    ) OR (
                        NOT EXISTS (
                            SELECT 1 FROM core_staffdivision sd
                            WHERE sd.staff_id = NEW.recorded_by_id
                              AND sd.division_id = NEW.division_id
                        )
                        AND NOT EXISTS (
                            SELECT 1 FROM core_staffrole sr
                            JOIN core_role r ON r.id = sr.role_id
                            WHERE sr.staff_id = NEW.recorded_by_id
                              AND r.code IN ('founder', 'super_admin')
                              AND sr.division_id IS NULL
                              AND sr.department_id IS NULL
                              AND sr.valid_from <= clock_timestamp()
                              AND (sr.valid_until IS NULL OR sr.valid_until > clock_timestamp())
                        )
                    ) THEN
                        RAISE EXCEPTION 'Customer communication division relationship is invalid';
                    END IF;
                ELSIF TG_TABLE_NAME = 'core_approvalrequest' THEN
                    IF (
                        NOT EXISTS (
                            SELECT 1 FROM core_staffdivision sd
                            WHERE sd.staff_id = NEW.requested_by_id
                              AND sd.division_id = NEW.division_id
                        )
                        AND NOT EXISTS (
                            SELECT 1 FROM core_staffrole sr
                            JOIN core_role r ON r.id = sr.role_id
                            WHERE sr.staff_id = NEW.requested_by_id
                              AND r.code IN ('founder', 'super_admin')
                              AND sr.division_id IS NULL
                              AND sr.department_id IS NULL
                              AND sr.valid_from <= clock_timestamp()
                              AND (sr.valid_until IS NULL OR sr.valid_until > clock_timestamp())
                        )
                    ) OR (
                        NEW.decided_by_id IS NOT NULL
                        AND NOT EXISTS (
                            SELECT 1 FROM core_staffdivision sd
                            WHERE sd.staff_id = NEW.decided_by_id
                              AND sd.division_id = NEW.division_id
                        )
                        AND NOT EXISTS (
                            SELECT 1 FROM core_staffrole sr
                            JOIN core_role r ON r.id = sr.role_id
                            WHERE sr.staff_id = NEW.decided_by_id
                              AND r.code IN ('founder', 'super_admin')
                              AND sr.division_id IS NULL
                              AND sr.department_id IS NULL
                              AND sr.valid_from <= clock_timestamp()
                              AND (sr.valid_until IS NULL OR sr.valid_until > clock_timestamp())
                        )
                    ) THEN
                        RAISE EXCEPTION 'Approval requester or decider division relationship is invalid';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        for table, base, columns in [
            ("core_customercommunication", "core_communication_scope",
             "customer_id, enquiry_id, division_id, recorded_by_id"),
            ("core_approvalrequest", "core_approval_request_scope",
             "division_id, requested_by_id, decided_by_id"),
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {base}_insert ON {table}")
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {base}_update ON {table}")
            schema_editor.execute(
                f"CREATE TRIGGER {base}_insert BEFORE INSERT ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION core_guard_crm_relationship_scope()"
            )
            schema_editor.execute(
                f"CREATE TRIGGER {base}_update BEFORE UPDATE OF {columns} ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION core_guard_crm_relationship_scope()"
            )


def remove_crm_relationship_scope_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        for name in [
            "core_communication_scope_insert", "core_communication_scope_update",
            "core_approval_request_scope_insert", "core_approval_request_scope_update",
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {name}")
    elif vendor == "postgresql":
        for table, base in [
            ("core_customercommunication", "core_communication_scope"),
            ("core_approvalrequest", "core_approval_request_scope"),
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {base}_insert ON {table}")
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {base}_update ON {table}")
        schema_editor.execute("DROP FUNCTION IF EXISTS core_guard_crm_relationship_scope()")


class Migration(migrations.Migration):
    dependencies = [("core", "0010_enquiry_followup_scope_guards")]
    operations = [
        migrations.RunPython(
            install_crm_relationship_scope_guards,
            reverse_code=remove_crm_relationship_scope_guards,
        ),
    ]
