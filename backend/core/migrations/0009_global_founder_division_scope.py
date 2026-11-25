from django.db import migrations


def install_global_founder_scope_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor

    if vendor == "sqlite":
        # Actor fields may use a global Founder/Super Admin role. Assigned workers
        # still require explicit StaffDivision membership.
        schema_editor.execute("DROP TRIGGER IF EXISTS core_orderassignment_division_insert")
        schema_editor.execute("DROP TRIGGER IF EXISTS core_orderassignment_division_update")
        order_assignment_invalid = """
            NOT EXISTS (
                SELECT 1 FROM core_salesorder o
                JOIN core_staffdivision sd ON sd.division_id = o.division_id
                    AND sd.staff_id = NEW.staff_id
                WHERE o.id = NEW.sales_order_id
            )
            OR (
                NOT EXISTS (
                    SELECT 1 FROM core_salesorder o
                    JOIN core_staffdivision sd ON sd.division_id = o.division_id
                        AND sd.staff_id = NEW.assigned_by_id
                    WHERE o.id = NEW.sales_order_id
                )
                AND NOT EXISTS (
                    SELECT 1 FROM core_salesorder o
                    JOIN core_staffrole sr ON sr.staff_id = NEW.assigned_by_id
                    JOIN core_role r ON r.id = sr.role_id
                    WHERE o.id = NEW.sales_order_id
                      AND r.code IN ('founder', 'super_admin')
                      AND sr.division_id IS NULL AND sr.department_id IS NULL
                      AND datetime(sr.valid_from) <= CURRENT_TIMESTAMP
                      AND (sr.valid_until IS NULL OR datetime(sr.valid_until) > CURRENT_TIMESTAMP)
                )
            )
        """
        schema_editor.execute(
            "CREATE TRIGGER core_orderassignment_division_insert BEFORE INSERT ON core_orderassignment "
            f"WHEN {order_assignment_invalid} BEGIN SELECT RAISE(ABORT, 'Cross-division order assignment'); END"
        )
        schema_editor.execute(
            "CREATE TRIGGER core_orderassignment_division_update BEFORE UPDATE OF sales_order_id, staff_id, assigned_by_id "
            "ON core_orderassignment "
            f"WHEN {order_assignment_invalid} BEGIN SELECT RAISE(ABORT, 'Cross-division order assignment'); END"
        )

        schema_editor.execute("DROP TRIGGER IF EXISTS core_stafftask_consistency_insert")
        schema_editor.execute("DROP TRIGGER IF EXISTS core_stafftask_consistency_update")
        task_invalid = """
            (NEW.sales_order_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM core_salesorder o
                WHERE o.id = NEW.sales_order_id AND o.division_id = NEW.division_id
            ))
            OR (NEW.job_card_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM core_jobcard j
                WHERE j.id = NEW.job_card_id AND j.division_id = NEW.division_id
                  AND (NEW.sales_order_id IS NULL OR j.sales_order_id = NEW.sales_order_id)
            ))
            OR (NEW.production_stage_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM core_productionstage p
                JOIN core_jobcard j ON j.id = p.job_card_id
                WHERE p.id = NEW.production_stage_id AND NEW.job_card_id IS NOT NULL
                  AND p.job_card_id = NEW.job_card_id AND j.division_id = NEW.division_id
            ))
            OR NOT EXISTS (
                SELECT 1 FROM core_staffdivision sd
                WHERE sd.staff_id = NEW.assigned_to_id AND sd.division_id = NEW.division_id
            )
            OR (
                NOT EXISTS (
                    SELECT 1 FROM core_staffdivision sd
                    WHERE sd.staff_id = NEW.assigned_by_id AND sd.division_id = NEW.division_id
                )
                AND NOT EXISTS (
                    SELECT 1 FROM core_staffrole sr
                    JOIN core_role r ON r.id = sr.role_id
                    WHERE sr.staff_id = NEW.assigned_by_id
                      AND r.code IN ('founder', 'super_admin')
                      AND sr.division_id IS NULL AND sr.department_id IS NULL
                      AND datetime(sr.valid_from) <= CURRENT_TIMESTAMP
                      AND (sr.valid_until IS NULL OR datetime(sr.valid_until) > CURRENT_TIMESTAMP)
                )
            )
        """
        schema_editor.execute(
            "CREATE TRIGGER core_stafftask_consistency_insert BEFORE INSERT ON core_stafftask "
            f"WHEN {task_invalid} BEGIN SELECT RAISE(ABORT, 'Cross-division task assignment'); END"
        )
        schema_editor.execute(
            "CREATE TRIGGER core_stafftask_consistency_update BEFORE UPDATE OF division_id, sales_order_id, job_card_id, production_stage_id, assigned_to_id, assigned_by_id "
            "ON core_stafftask "
            f"WHEN {task_invalid} BEGIN SELECT RAISE(ABORT, 'Cross-division task assignment'); END"
        )

        for table, insert_name, update_name, actor_fields, columns in [
            ("core_quotation", "core_quotation_scope_insert", "core_quotation_scope_update",
             ["prepared_by_id", "approved_by_id"], "division_id, customer_id, enquiry_id, prepared_by_id, approved_by_id"),
            ("core_salesorder", "core_salesorder_scope_insert", "core_salesorder_scope_update",
             ["created_by_id"], "division_id, customer_id, quotation_id, created_by_id"),
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {insert_name}")
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {update_name}")
            if table == "core_quotation":
                invalid = """
                    (NEW.enquiry_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_enquiry e WHERE e.id = NEW.enquiry_id
                          AND e.division_id = NEW.division_id AND e.customer_id = NEW.customer_id
                    ))
                    OR (
                        NOT EXISTS (SELECT 1 FROM core_staffdivision sd
                            WHERE sd.staff_id = NEW.prepared_by_id AND sd.division_id = NEW.division_id)
                        AND NOT EXISTS (SELECT 1 FROM core_staffrole sr
                            JOIN core_role r ON r.id = sr.role_id
                            WHERE sr.staff_id = NEW.prepared_by_id
                              AND r.code IN ('founder', 'super_admin')
                              AND sr.division_id IS NULL AND sr.department_id IS NULL
                              AND datetime(sr.valid_from) <= CURRENT_TIMESTAMP
                              AND (sr.valid_until IS NULL OR datetime(sr.valid_until) > CURRENT_TIMESTAMP))
                    )
                    OR (NEW.approved_by_id IS NOT NULL AND
                        NOT EXISTS (SELECT 1 FROM core_staffdivision sd
                            WHERE sd.staff_id = NEW.approved_by_id AND sd.division_id = NEW.division_id)
                        AND NOT EXISTS (SELECT 1 FROM core_staffrole sr
                            JOIN core_role r ON r.id = sr.role_id
                            WHERE sr.staff_id = NEW.approved_by_id
                              AND r.code IN ('founder', 'super_admin')
                              AND sr.division_id IS NULL AND sr.department_id IS NULL
                              AND datetime(sr.valid_from) <= CURRENT_TIMESTAMP
                              AND (sr.valid_until IS NULL OR datetime(sr.valid_until) > CURRENT_TIMESTAMP))
                    )
                """
            else:
                invalid = """
                    (NEW.quotation_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_quotation q WHERE q.id = NEW.quotation_id
                          AND q.division_id = NEW.division_id AND q.customer_id = NEW.customer_id
                    ))
                    OR (
                        NOT EXISTS (SELECT 1 FROM core_staffdivision sd
                            WHERE sd.staff_id = NEW.created_by_id AND sd.division_id = NEW.division_id)
                        AND NOT EXISTS (SELECT 1 FROM core_staffrole sr
                            JOIN core_role r ON r.id = sr.role_id
                            WHERE sr.staff_id = NEW.created_by_id
                              AND r.code IN ('founder', 'super_admin')
                              AND sr.division_id IS NULL AND sr.department_id IS NULL
                              AND datetime(sr.valid_from) <= CURRENT_TIMESTAMP
                              AND (sr.valid_until IS NULL OR datetime(sr.valid_until) > CURRENT_TIMESTAMP))
                    )
                """
            schema_editor.execute(
                f"CREATE TRIGGER {insert_name} BEFORE INSERT ON {table} WHEN {invalid} "
                "BEGIN SELECT RAISE(ABORT, 'Commercial division relationship is invalid'); END"
            )
            schema_editor.execute(
                f"CREATE TRIGGER {update_name} BEFORE UPDATE OF {columns} ON {table} WHEN {invalid} "
                "BEGIN SELECT RAISE(ABORT, 'Commercial division relationship is invalid'); END"
            )

    elif vendor == "postgresql":
        schema_editor.execute("""
            CREATE OR REPLACE FUNCTION core_guard_division_assignments()
            RETURNS trigger AS $$
            DECLARE
                target_division uuid;
            BEGIN
                IF TG_TABLE_NAME = 'core_orderassignment' THEN
                    SELECT division_id INTO target_division FROM core_salesorder WHERE id = NEW.sales_order_id;
                    IF NOT EXISTS (SELECT 1 FROM core_staffdivision
                        WHERE staff_id = NEW.staff_id AND division_id = target_division) THEN
                        RAISE EXCEPTION 'Assigned staff must belong to the sales order division';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM core_staffdivision
                        WHERE staff_id = NEW.assigned_by_id AND division_id = target_division)
                       AND NOT EXISTS (
                        SELECT 1 FROM core_staffrole sr JOIN core_role r ON r.id = sr.role_id
                        WHERE sr.staff_id = NEW.assigned_by_id
                          AND r.code IN ('founder', 'super_admin')
                          AND sr.division_id IS NULL AND sr.department_id IS NULL
                          AND sr.valid_from <= clock_timestamp()
                          AND (sr.valid_until IS NULL OR sr.valid_until > clock_timestamp())
                       ) THEN
                        RAISE EXCEPTION 'Assigner must belong to the division or hold a global Founder/Super Admin role';
                    END IF;
                ELSIF TG_TABLE_NAME = 'core_designrecord' THEN
                    IF NEW.assigned_to_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_salesorder o JOIN core_staffdivision sd
                          ON sd.division_id = o.division_id AND sd.staff_id = NEW.assigned_to_id
                        WHERE o.id = NEW.sales_order_id
                    ) THEN RAISE EXCEPTION 'Design assignee must belong to the sales order division'; END IF;
                ELSIF TG_TABLE_NAME = 'core_productionstage' THEN
                    IF NEW.assigned_to_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_jobcard j JOIN core_staffdivision sd
                          ON sd.division_id = j.division_id AND sd.staff_id = NEW.assigned_to_id
                        WHERE j.id = NEW.job_card_id
                    ) THEN RAISE EXCEPTION 'Production assignee must belong to the job card division'; END IF;
                ELSIF TG_TABLE_NAME = 'core_productionupdate' THEN
                    IF NOT EXISTS (
                        SELECT 1 FROM core_productionstage p JOIN core_jobcard j ON j.id = p.job_card_id
                        JOIN core_staffdivision sd ON sd.division_id = j.division_id AND sd.staff_id = NEW.staff_id
                        WHERE p.id = NEW.production_stage_id
                    ) THEN RAISE EXCEPTION 'Production reporter must belong to the job card division'; END IF;
                ELSIF TG_TABLE_NAME = 'core_stafftask' THEN
                    IF (NEW.sales_order_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_salesorder o WHERE o.id = NEW.sales_order_id AND o.division_id = NEW.division_id
                    )) OR (NEW.job_card_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_jobcard j WHERE j.id = NEW.job_card_id AND j.division_id = NEW.division_id
                          AND (NEW.sales_order_id IS NULL OR j.sales_order_id = NEW.sales_order_id)
                    )) OR (NEW.production_stage_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_productionstage p JOIN core_jobcard j ON j.id = p.job_card_id
                        WHERE p.id = NEW.production_stage_id AND NEW.job_card_id IS NOT NULL
                          AND p.job_card_id = NEW.job_card_id AND j.division_id = NEW.division_id
                    )) OR NOT EXISTS (
                        SELECT 1 FROM core_staffdivision WHERE staff_id = NEW.assigned_to_id AND division_id = NEW.division_id
                    ) OR (
                        NOT EXISTS (SELECT 1 FROM core_staffdivision
                            WHERE staff_id = NEW.assigned_by_id AND division_id = NEW.division_id)
                        AND NOT EXISTS (SELECT 1 FROM core_staffrole sr JOIN core_role r ON r.id = sr.role_id
                            WHERE sr.staff_id = NEW.assigned_by_id
                              AND r.code IN ('founder', 'super_admin')
                              AND sr.division_id IS NULL AND sr.department_id IS NULL
                              AND sr.valid_from <= clock_timestamp()
                              AND (sr.valid_until IS NULL OR sr.valid_until > clock_timestamp()))
                    ) THEN RAISE EXCEPTION 'Cross-division task assignment or inconsistent task relationship'; END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        schema_editor.execute("""
            CREATE OR REPLACE FUNCTION core_guard_commercial_scope()
            RETURNS trigger AS $$
            BEGIN
                IF TG_TABLE_NAME = 'core_quotation' THEN
                    IF (NEW.enquiry_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_enquiry e WHERE e.id = NEW.enquiry_id
                          AND e.division_id = NEW.division_id AND e.customer_id = NEW.customer_id
                    )) OR (
                        NOT EXISTS (SELECT 1 FROM core_staffdivision
                            WHERE staff_id = NEW.prepared_by_id AND division_id = NEW.division_id)
                        AND NOT EXISTS (SELECT 1 FROM core_staffrole sr JOIN core_role r ON r.id = sr.role_id
                            WHERE sr.staff_id = NEW.prepared_by_id AND r.code IN ('founder', 'super_admin')
                              AND sr.division_id IS NULL AND sr.department_id IS NULL
                              AND sr.valid_from <= clock_timestamp()
                              AND (sr.valid_until IS NULL OR sr.valid_until > clock_timestamp()))
                    ) OR (NEW.approved_by_id IS NOT NULL AND
                        NOT EXISTS (SELECT 1 FROM core_staffdivision
                            WHERE staff_id = NEW.approved_by_id AND division_id = NEW.division_id)
                        AND NOT EXISTS (SELECT 1 FROM core_staffrole sr JOIN core_role r ON r.id = sr.role_id
                            WHERE sr.staff_id = NEW.approved_by_id AND r.code IN ('founder', 'super_admin')
                              AND sr.division_id IS NULL AND sr.department_id IS NULL
                              AND sr.valid_from <= clock_timestamp()
                              AND (sr.valid_until IS NULL OR sr.valid_until > clock_timestamp()))
                    ) THEN RAISE EXCEPTION 'Quotation division, enquiry, customer, or staff relationship is invalid'; END IF;
                ELSIF TG_TABLE_NAME = 'core_salesorder' THEN
                    IF (NEW.quotation_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_quotation q WHERE q.id = NEW.quotation_id
                          AND q.division_id = NEW.division_id AND q.customer_id = NEW.customer_id
                    )) OR (
                        NOT EXISTS (SELECT 1 FROM core_staffdivision
                            WHERE staff_id = NEW.created_by_id AND division_id = NEW.division_id)
                        AND NOT EXISTS (SELECT 1 FROM core_staffrole sr JOIN core_role r ON r.id = sr.role_id
                            WHERE sr.staff_id = NEW.created_by_id AND r.code IN ('founder', 'super_admin')
                              AND sr.division_id IS NULL AND sr.department_id IS NULL
                              AND sr.valid_from <= clock_timestamp()
                              AND (sr.valid_until IS NULL OR sr.valid_until > clock_timestamp()))
                    ) THEN RAISE EXCEPTION 'Sales order division, quotation, customer, or creator relationship is invalid'; END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
    # Existing PostgreSQL triggers call the replaced functions; SQLite triggers
    # were recreated above with the updated actor-scope predicates.


class Migration(migrations.Migration):
    dependencies = [("core", "0008_commercial_scope_database_guards")]
    operations = [
        migrations.RunPython(install_global_founder_scope_guards, migrations.RunPython.noop),
    ]
