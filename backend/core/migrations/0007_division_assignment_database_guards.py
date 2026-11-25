from django.db import migrations


def install_division_assignment_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor

    sqlite_triggers = {
        "core_orderassignment": (
            "core_orderassignment_division_insert",
            "core_orderassignment_division_update",
            """
            NOT EXISTS (
                SELECT 1 FROM core_salesorder o
                JOIN core_staffdivision sd_staff
                  ON sd_staff.division_id = o.division_id
                 AND sd_staff.staff_id = NEW.staff_id
                JOIN core_staffdivision sd_assigner
                  ON sd_assigner.division_id = o.division_id
                 AND sd_assigner.staff_id = NEW.assigned_by_id
                WHERE o.id = NEW.sales_order_id
            )
            """,
            "INSERT OR UPDATE OF sales_order_id, staff_id, assigned_by_id",
        ),
        "core_designrecord": (
            "core_designrecord_assignee_insert",
            "core_designrecord_assignee_update",
            """
            NEW.assigned_to_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM core_salesorder o
                JOIN core_staffdivision sd
                  ON sd.division_id = o.division_id
                 AND sd.staff_id = NEW.assigned_to_id
                WHERE o.id = NEW.sales_order_id
            )
            """,
            "INSERT OR UPDATE OF sales_order_id, assigned_to_id",
        ),
        "core_productionstage": (
            "core_productionstage_assignee_insert",
            "core_productionstage_assignee_update",
            """
            NEW.assigned_to_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM core_jobcard j
                JOIN core_staffdivision sd
                  ON sd.division_id = j.division_id
                 AND sd.staff_id = NEW.assigned_to_id
                WHERE j.id = NEW.job_card_id
            )
            """,
            "INSERT OR UPDATE OF job_card_id, assigned_to_id",
        ),
        "core_productionupdate": (
            "core_productionupdate_staff_insert",
            "core_productionupdate_staff_update",
            """
            NOT EXISTS (
                SELECT 1 FROM core_productionstage p
                JOIN core_jobcard j ON j.id = p.job_card_id
                JOIN core_staffdivision sd
                  ON sd.division_id = j.division_id
                 AND sd.staff_id = NEW.staff_id
                WHERE p.id = NEW.production_stage_id
            )
            """,
            "INSERT OR UPDATE OF production_stage_id, staff_id",
        ),
        "core_stafftask": (
            "core_stafftask_consistency_insert",
            "core_stafftask_consistency_update",
            """
            (
                (NEW.sales_order_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM core_salesorder o
                    WHERE o.id = NEW.sales_order_id
                      AND o.division_id = NEW.division_id
                ))
                OR
                (NEW.job_card_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM core_jobcard j
                    WHERE j.id = NEW.job_card_id
                      AND j.division_id = NEW.division_id
                      AND (NEW.sales_order_id IS NULL OR j.sales_order_id = NEW.sales_order_id)
                ))
                OR
                (NEW.production_stage_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM core_productionstage p
                    JOIN core_jobcard j ON j.id = p.job_card_id
                    WHERE p.id = NEW.production_stage_id
                      AND NEW.job_card_id IS NOT NULL
                      AND p.job_card_id = NEW.job_card_id
                      AND j.division_id = NEW.division_id
                ))
                OR NOT EXISTS (
                    SELECT 1 FROM core_staffdivision sd
                    WHERE sd.staff_id = NEW.assigned_to_id
                      AND sd.division_id = NEW.division_id
                )
                OR NOT EXISTS (
                    SELECT 1 FROM core_staffdivision sd
                    WHERE sd.staff_id = NEW.assigned_by_id
                      AND sd.division_id = NEW.division_id
                )
            )
            """,
            "INSERT OR UPDATE OF division_id, sales_order_id, job_card_id, production_stage_id, assigned_to_id, assigned_by_id",
        ),
    }

    if vendor == "sqlite":
        for table, (insert_name, update_name, invalid, event) in sqlite_triggers.items():
            schema_editor.execute(
                f"CREATE TRIGGER IF NOT EXISTS {insert_name} BEFORE INSERT ON {table} "
                f"WHEN {invalid} BEGIN SELECT RAISE(ABORT, 'Cross-division assignment or inconsistent task relationship'); END"
            )
            update_columns = event.replace("INSERT OR ", "")
            schema_editor.execute(
                f"CREATE TRIGGER IF NOT EXISTS {update_name} BEFORE UPDATE OF "
                f"{update_columns.split('UPDATE OF ', 1)[1]} ON {table} "
                f"WHEN {invalid} BEGIN SELECT RAISE(ABORT, 'Cross-division assignment or inconsistent task relationship'); END"
            )
    elif vendor == "postgresql":
        schema_editor.execute(
            """
            CREATE OR REPLACE FUNCTION core_guard_division_assignments()
            RETURNS trigger AS $$
            BEGIN
                IF TG_TABLE_NAME = 'core_orderassignment' THEN
                    IF NOT EXISTS (
                        SELECT 1 FROM core_salesorder o
                        JOIN core_staffdivision sd_staff
                          ON sd_staff.division_id = o.division_id AND sd_staff.staff_id = NEW.staff_id
                        JOIN core_staffdivision sd_assigner
                          ON sd_assigner.division_id = o.division_id AND sd_assigner.staff_id = NEW.assigned_by_id
                        WHERE o.id = NEW.sales_order_id
                    ) THEN
                        RAISE EXCEPTION 'Order assignment staff must belong to the sales order division';
                    END IF;
                ELSIF TG_TABLE_NAME = 'core_designrecord' THEN
                    IF NEW.assigned_to_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_salesorder o
                        JOIN core_staffdivision sd
                          ON sd.division_id = o.division_id AND sd.staff_id = NEW.assigned_to_id
                        WHERE o.id = NEW.sales_order_id
                    ) THEN
                        RAISE EXCEPTION 'Design assignee must belong to the sales order division';
                    END IF;
                ELSIF TG_TABLE_NAME = 'core_productionstage' THEN
                    IF NEW.assigned_to_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_jobcard j
                        JOIN core_staffdivision sd
                          ON sd.division_id = j.division_id AND sd.staff_id = NEW.assigned_to_id
                        WHERE j.id = NEW.job_card_id
                    ) THEN
                        RAISE EXCEPTION 'Production assignee must belong to the job card division';
                    END IF;
                ELSIF TG_TABLE_NAME = 'core_productionupdate' THEN
                    IF NOT EXISTS (
                        SELECT 1 FROM core_productionstage p
                        JOIN core_jobcard j ON j.id = p.job_card_id
                        JOIN core_staffdivision sd
                          ON sd.division_id = j.division_id AND sd.staff_id = NEW.staff_id
                        WHERE p.id = NEW.production_stage_id
                    ) THEN
                        RAISE EXCEPTION 'Production reporter must belong to the job card division';
                    END IF;
                ELSIF TG_TABLE_NAME = 'core_stafftask' THEN
                    IF (NEW.sales_order_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_salesorder o
                        WHERE o.id = NEW.sales_order_id AND o.division_id = NEW.division_id
                    )) OR (NEW.job_card_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_jobcard j
                        WHERE j.id = NEW.job_card_id AND j.division_id = NEW.division_id
                          AND (NEW.sales_order_id IS NULL OR j.sales_order_id = NEW.sales_order_id)
                    )) OR (NEW.production_stage_id IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_productionstage p
                        JOIN core_jobcard j ON j.id = p.job_card_id
                        WHERE p.id = NEW.production_stage_id
                          AND NEW.job_card_id IS NOT NULL
                          AND p.job_card_id = NEW.job_card_id
                          AND j.division_id = NEW.division_id
                    )) OR NOT EXISTS (
                        SELECT 1 FROM core_staffdivision sd
                        WHERE sd.staff_id = NEW.assigned_to_id AND sd.division_id = NEW.division_id
                    ) OR NOT EXISTS (
                        SELECT 1 FROM core_staffdivision sd
                        WHERE sd.staff_id = NEW.assigned_by_id AND sd.division_id = NEW.division_id
                    ) THEN
                        RAISE EXCEPTION 'Cross-division assignment or inconsistent task relationship';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        triggers = [
            ("core_orderassignment", "core_orderassignment_division_guard", "INSERT OR UPDATE OF sales_order_id, staff_id, assigned_by_id"),
            ("core_designrecord", "core_designrecord_assignee_guard", "INSERT OR UPDATE OF sales_order_id, assigned_to_id"),
            ("core_productionstage", "core_productionstage_assignee_guard", "INSERT OR UPDATE OF job_card_id, assigned_to_id"),
            ("core_productionupdate", "core_productionupdate_staff_guard", "INSERT OR UPDATE OF production_stage_id, staff_id"),
            ("core_stafftask", "core_stafftask_consistency_guard", "INSERT OR UPDATE OF division_id, sales_order_id, job_card_id, production_stage_id, assigned_to_id, assigned_by_id"),
        ]
        for table, trigger, events in triggers:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
            schema_editor.execute(
                f"CREATE TRIGGER {trigger} BEFORE {events} ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION core_guard_division_assignments()"
            )


def remove_division_assignment_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        for trigger in [
            "core_orderassignment_division_insert", "core_orderassignment_division_update",
            "core_designrecord_assignee_insert", "core_designrecord_assignee_update",
            "core_productionstage_assignee_insert", "core_productionstage_assignee_update",
            "core_productionupdate_staff_insert", "core_productionupdate_staff_update",
            "core_stafftask_consistency_insert", "core_stafftask_consistency_update",
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger}")
    elif vendor == "postgresql":
        for table, trigger in [
            ("core_orderassignment", "core_orderassignment_division_guard"),
            ("core_designrecord", "core_designrecord_assignee_guard"),
            ("core_productionstage", "core_productionstage_assignee_guard"),
            ("core_productionupdate", "core_productionupdate_staff_guard"),
            ("core_stafftask", "core_stafftask_consistency_guard"),
        ]:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
        schema_editor.execute("DROP FUNCTION IF EXISTS core_guard_division_assignments()")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_job_card_release_database_guards"),
    ]

    operations = [
        migrations.RunPython(
            install_division_assignment_guards,
            reverse_code=remove_division_assignment_guards,
        ),
    ]
