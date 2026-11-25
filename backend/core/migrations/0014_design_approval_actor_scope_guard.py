from django.db import migrations


def install_design_approval_actor_guard(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        invalid = """
            NEW.reviewer_type NOT IN ('customer', 'manager')
            OR NEW.decision NOT IN ('approved', 'revision_required')
            OR NEW.reviewed_by_id IS NULL
            OR NEW.reviewed_at IS NULL
            OR EXISTS (
                SELECT 1 FROM core_designrevision locked_rev
                WHERE locked_rev.id = NEW.design_revision_id
                  AND locked_rev.locked_at IS NOT NULL
            )
            OR NOT EXISTS (
                SELECT 1
                FROM core_designrevision rev
                JOIN core_designrecord dr ON dr.id = rev.design_record_id
                JOIN core_salesorder so ON so.id = dr.sales_order_id
                JOIN core_staffprofile sp ON sp.id = NEW.reviewed_by_id
                WHERE rev.id = NEW.design_revision_id
                  AND sp.employment_status = 'active'
                  AND EXISTS (
                      SELECT 1
                      FROM core_staffrole sr
                      JOIN core_role r ON r.id = sr.role_id
                      LEFT JOIN core_department dep ON dep.id = sr.department_id
                      WHERE sr.staff_id = sp.id
                        AND datetime(sr.valid_from) <= CURRENT_TIMESTAMP
                        AND (sr.valid_until IS NULL OR datetime(sr.valid_until) > CURRENT_TIMESTAMP)
                        AND (
                            (r.code IN ('founder', 'super_admin')
                             AND sr.division_id IS NULL AND sr.department_id IS NULL)
                            OR
                            (r.code = 'manager' AND (
                                (sr.division_id IS NULL AND sr.department_id IS NULL)
                                OR (sr.division_id = so.division_id
                                    AND (sr.department_id IS NULL OR dep.division_id = so.division_id))
                                OR (sr.division_id IS NULL AND sr.department_id IS NOT NULL
                                    AND dep.division_id = so.division_id)
                            ))
                        )
                  )
            )
            OR (
                NEW.reviewer_type = 'manager'
                AND NEW.decision = 'approved'
                AND NOT EXISTS (
                    SELECT 1
                    FROM core_designapproval ca
                    WHERE ca.design_revision_id = NEW.design_revision_id
                      AND ca.reviewer_type = 'customer'
                      AND ca.decision = 'approved'
                      AND NOT EXISTS (
                          SELECT 1
                          FROM core_designapproval newer
                          WHERE newer.design_revision_id = ca.design_revision_id
                            AND newer.reviewer_type = 'customer'
                            AND (
                                datetime(newer.reviewed_at) > datetime(ca.reviewed_at)
                                OR (datetime(newer.reviewed_at) = datetime(ca.reviewed_at)
                                    AND newer.id > ca.id)
                            )
                      )
                )
            )
        """
        schema_editor.execute(
            "CREATE TRIGGER core_designapproval_actor_insert "
            "BEFORE INSERT ON core_designapproval "
            f"WHEN {invalid} "
            "BEGIN SELECT RAISE(ABORT, 'Design approval actor or workflow scope is invalid'); END"
        )
    elif vendor == "postgresql":
        schema_editor.execute("""
            CREATE OR REPLACE FUNCTION core_guard_designapproval_actor()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.reviewer_type NOT IN ('customer', 'manager')
                   OR NEW.decision NOT IN ('approved', 'revision_required')
                   OR NEW.reviewed_by_id IS NULL
                   OR NEW.reviewed_at IS NULL
                   OR EXISTS (
                       SELECT 1 FROM core_designrevision locked_rev
                       WHERE locked_rev.id = NEW.design_revision_id
                         AND locked_rev.locked_at IS NOT NULL
                   )
                   OR NOT EXISTS (
                       SELECT 1
                       FROM core_designrevision rev
                       JOIN core_designrecord dr ON dr.id = rev.design_record_id
                       JOIN core_salesorder so ON so.id = dr.sales_order_id
                       JOIN core_staffprofile sp ON sp.id = NEW.reviewed_by_id
                       WHERE rev.id = NEW.design_revision_id
                         AND sp.employment_status = 'active'
                         AND EXISTS (
                             SELECT 1
                             FROM core_staffrole sr
                             JOIN core_role r ON r.id = sr.role_id
                             LEFT JOIN core_department dep ON dep.id = sr.department_id
                             WHERE sr.staff_id = sp.id
                               AND sr.valid_from <= clock_timestamp()
                               AND (sr.valid_until IS NULL OR sr.valid_until > clock_timestamp())
                               AND (
                                   (r.code IN ('founder', 'super_admin')
                                    AND sr.division_id IS NULL AND sr.department_id IS NULL)
                                   OR
                                   (r.code = 'manager' AND (
                                       (sr.division_id IS NULL AND sr.department_id IS NULL)
                                       OR (sr.division_id = so.division_id
                                           AND (sr.department_id IS NULL OR dep.division_id = so.division_id))
                                       OR (sr.division_id IS NULL AND sr.department_id IS NOT NULL
                                           AND dep.division_id = so.division_id)
                                   ))
                               )
                         )
                   )
                   OR (
                       NEW.reviewer_type = 'manager'
                       AND NEW.decision = 'approved'
                       AND NOT EXISTS (
                           SELECT 1
                           FROM core_designapproval ca
                           WHERE ca.design_revision_id = NEW.design_revision_id
                             AND ca.reviewer_type = 'customer'
                             AND ca.decision = 'approved'
                             AND NOT EXISTS (
                                 SELECT 1
                                 FROM core_designapproval newer
                                 WHERE newer.design_revision_id = ca.design_revision_id
                                   AND newer.reviewer_type = 'customer'
                                   AND (
                                       newer.reviewed_at > ca.reviewed_at
                                       OR (newer.reviewed_at = ca.reviewed_at AND newer.id > ca.id)
                                   )
                             )
                       )
                   ) THEN
                    RAISE EXCEPTION 'Design approval actor or workflow scope is invalid';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        schema_editor.execute(
            "CREATE TRIGGER core_designapproval_actor_guard "
            "BEFORE INSERT ON core_designapproval "
            "FOR EACH ROW EXECUTE FUNCTION core_guard_designapproval_actor()"
        )


def remove_design_approval_actor_guard(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        schema_editor.execute("DROP TRIGGER IF EXISTS core_designapproval_actor_insert")
    elif vendor == "postgresql":
        schema_editor.execute(
            "DROP TRIGGER IF EXISTS core_designapproval_actor_guard ON core_designapproval"
        )
        schema_editor.execute("DROP FUNCTION IF EXISTS core_guard_designapproval_actor()")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_staff_role_department_scope_guard"),
    ]

    operations = [
        migrations.RunPython(
            install_design_approval_actor_guard,
            reverse_code=remove_design_approval_actor_guard,
        ),
    ]
