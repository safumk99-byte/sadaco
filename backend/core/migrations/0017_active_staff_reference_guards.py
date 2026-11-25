from django.db import migrations


STAFF_REFERENCE_COLUMNS = {
    "core_staffdivision": [
        "staff_id"
    ],
    "core_staffdepartment": [
        "staff_id"
    ],
    "core_staffrole": [
        "staff_id",
        "granted_by_id"
    ],
    "core_enquiry": [
        "assigned_to_id",
        "created_by_id"
    ],
    "core_followup": [
        "assigned_to_id"
    ],
    "core_customercommunication": [
        "recorded_by_id"
    ],
    "core_approvalrequest": [
        "requested_by_id",
        "decided_by_id"
    ],
    "core_quotation": [
        "prepared_by_id",
        "approved_by_id"
    ],
    "core_salesorder": [
        "created_by_id"
    ],
    "core_orderassignment": [
        "staff_id",
        "assigned_by_id"
    ],
    "core_orderstatusevent": [
        "changed_by_id"
    ],
    "core_designrecord": [
        "assigned_to_id"
    ],
    "core_designrevision": [
        "created_by_id"
    ],
    "core_designapproval": [
        "reviewed_by_id"
    ],
    "core_storedfile": [
        "uploaded_by_id"
    ],
    "core_productionstage": [
        "assigned_to_id"
    ],
    "core_productionupdate": [
        "staff_id"
    ],
    "core_stafftask": [
        "assigned_to_id",
        "assigned_by_id"
    ],
    "core_taskupdate": [
        "reported_by_id"
    ],
    "core_auditevent": [
        "actor_id"
    ]
}


def install_active_staff_reference_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        for table, columns in STAFF_REFERENCE_COLUMNS.items():
            invalid = " OR ".join(
                f"(NEW.{column} IS NOT NULL AND NOT EXISTS ("
                "SELECT 1 FROM core_staffprofile sp "
                f"WHERE sp.id = NEW.{column} AND sp.employment_status = 'active'))"
                for column in columns
            )
            trigger_base = table.replace("core_", "core_active_staff_")
            schema_editor.execute(
                f"CREATE TRIGGER {trigger_base}_insert BEFORE INSERT ON {table} "
                f"WHEN {invalid} BEGIN SELECT RAISE(ABORT, 'Only active staff may be referenced'); END"
            )
            update_columns = ", ".join(columns)
            schema_editor.execute(
                f"CREATE TRIGGER {trigger_base}_update BEFORE UPDATE OF {update_columns} ON {table} "
                f"WHEN {invalid} BEGIN SELECT RAISE(ABORT, 'Only active staff may be referenced'); END"
            )
    elif vendor == "postgresql":
        schema_editor.execute("""
            CREATE OR REPLACE FUNCTION core_guard_active_staff_reference()
            RETURNS trigger AS $$
            DECLARE
                field_name text;
                staff_id_text text;
            BEGIN
                FOREACH field_name IN ARRAY TG_ARGV LOOP
                    staff_id_text := to_jsonb(NEW) ->> field_name;
                    IF staff_id_text IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM core_staffprofile sp
                        WHERE sp.id = staff_id_text::uuid
                          AND sp.employment_status = 'active'
                    ) THEN
                        RAISE EXCEPTION 'Only active staff may be referenced';
                    END IF;
                END LOOP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        for table, columns in STAFF_REFERENCE_COLUMNS.items():
            trigger_base = table.replace("core_", "core_active_staff_")
            args = ", ".join(f"'{column}'" for column in columns)
            schema_editor.execute(
                f"CREATE TRIGGER {trigger_base}_insert BEFORE INSERT ON {table} "
                f"FOR EACH ROW EXECUTE FUNCTION core_guard_active_staff_reference({args})"
            )
            schema_editor.execute(
                f"CREATE TRIGGER {trigger_base}_update BEFORE UPDATE OF {', '.join(columns)} ON {table} "
                f"FOR EACH ROW EXECUTE FUNCTION core_guard_active_staff_reference({args})"
            )


def remove_active_staff_reference_guards(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        for table in STAFF_REFERENCE_COLUMNS:
            trigger_base = table.replace("core_", "core_active_staff_")
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger_base}_insert")
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger_base}_update")
    elif vendor == "postgresql":
        for table in STAFF_REFERENCE_COLUMNS:
            trigger_base = table.replace("core_", "core_active_staff_")
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger_base}_insert ON {table}")
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger_base}_update ON {table}")
        schema_editor.execute("DROP FUNCTION IF EXISTS core_guard_active_staff_reference()")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0016_department_division_immutability"),
    ]

    operations = [
        migrations.RunPython(
            install_active_staff_reference_guards,
            reverse_code=remove_active_staff_reference_guards,
        ),
    ]
