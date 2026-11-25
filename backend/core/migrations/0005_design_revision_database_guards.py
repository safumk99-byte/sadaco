from django.db import migrations


def install_design_revision_guards(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor
    table = connection.ops.quote_name("core_designrevision")

    if vendor == "sqlite":
        schema_editor.execute(
            f"CREATE TRIGGER IF NOT EXISTS core_designrevision_reject_unapproved_insert "
            f"BEFORE INSERT ON {table} "
            "WHEN NEW.locked_at IS NOT NULL OR NEW.status = 'approved' "
            "BEGIN SELECT RAISE(ABORT, 'Design revisions must be approved through the workflow'); END"
        )
        schema_editor.execute(
            f"CREATE TRIGGER IF NOT EXISTS core_designrevision_immutable_update "
            f"BEFORE UPDATE ON {table} "
            "WHEN OLD.locked_at IS NOT NULL "
            "BEGIN SELECT RAISE(ABORT, 'Approved design revisions are immutable'); END"
        )
        schema_editor.execute(
            f"CREATE TRIGGER IF NOT EXISTS core_designrevision_immutable_delete "
            f"BEFORE DELETE ON {table} "
            "WHEN OLD.locked_at IS NOT NULL "
            "BEGIN SELECT RAISE(ABORT, 'Approved design revisions cannot be deleted'); END"
        )
        schema_editor.execute(
            f"CREATE TRIGGER IF NOT EXISTS core_designrevision_require_approval_lock "
            f"BEFORE UPDATE ON {table} "
            "WHEN OLD.locked_at IS NULL AND NEW.locked_at IS NOT NULL "
            "AND (NEW.status <> 'approved' "
            "OR NOT EXISTS (SELECT 1 FROM core_designapproval a "
            "WHERE a.design_revision_id = NEW.id "
            "AND a.reviewer_type = 'customer' AND a.decision = 'approved') "
            "OR NOT EXISTS (SELECT 1 FROM core_designapproval a "
            "WHERE a.design_revision_id = NEW.id "
            "AND a.reviewer_type = 'manager' AND a.decision = 'approved')) "
            "BEGIN SELECT RAISE(ABORT, 'Customer and Manager approvals are required'); END"
        )
        attachment_table = connection.ops.quote_name("core_designrevisionfile")
        schema_editor.execute(
            f"CREATE TRIGGER IF NOT EXISTS core_designrevisionfile_reject_locked_insert "
            f"BEFORE INSERT ON {attachment_table} "
            "WHEN EXISTS (SELECT 1 FROM core_designrevision r "
            "WHERE r.id = NEW.design_revision_id AND r.locked_at IS NOT NULL) "
            "BEGIN SELECT RAISE(ABORT, 'Files cannot be attached to an approved design revision'); END"
        )
        schema_editor.execute(
            f"CREATE TRIGGER IF NOT EXISTS core_designrevisionfile_reject_locked_update "
            f"BEFORE UPDATE ON {attachment_table} "
            "WHEN EXISTS (SELECT 1 FROM core_designrevision r "
            "WHERE r.id = OLD.design_revision_id AND r.locked_at IS NOT NULL) "
            "OR EXISTS (SELECT 1 FROM core_designrevision r "
            "WHERE r.id = NEW.design_revision_id AND r.locked_at IS NOT NULL) "
            "BEGIN SELECT RAISE(ABORT, 'Files attached to an approved design revision are immutable'); END"
        )
        schema_editor.execute(
            f"CREATE TRIGGER IF NOT EXISTS core_designrevisionfile_reject_locked_delete "
            f"BEFORE DELETE ON {attachment_table} "
            "WHEN EXISTS (SELECT 1 FROM core_designrevision r "
            "WHERE r.id = OLD.design_revision_id AND r.locked_at IS NOT NULL) "
            "BEGIN SELECT RAISE(ABORT, 'Files attached to an approved design revision cannot be removed'); END"
        )
    elif vendor == "postgresql":
        schema_editor.execute(
            """
            CREATE OR REPLACE FUNCTION core_guard_designrevision_mutation()
            RETURNS trigger AS $$
            BEGIN
                IF TG_OP = 'INSERT' THEN
                    IF NEW.locked_at IS NOT NULL OR NEW.status = 'approved' THEN
                        RAISE EXCEPTION 'Design revisions must be approved through the workflow';
                    END IF;
                    RETURN NEW;
                END IF;

                IF TG_OP = 'DELETE' THEN
                    IF OLD.locked_at IS NOT NULL THEN
                        RAISE EXCEPTION 'Approved design revisions cannot be deleted';
                    END IF;
                    RETURN OLD;
                END IF;

                IF OLD.locked_at IS NOT NULL THEN
                    RAISE EXCEPTION 'Approved design revisions are immutable';
                END IF;

                IF OLD.locked_at IS NULL AND NEW.locked_at IS NOT NULL THEN
                    IF NEW.status <> 'approved'
                       OR NOT EXISTS (
                           SELECT 1 FROM core_designapproval a
                           WHERE a.design_revision_id = NEW.id
                             AND a.reviewer_type = 'customer'
                             AND a.decision = 'approved'
                       )
                       OR NOT EXISTS (
                           SELECT 1 FROM core_designapproval a
                           WHERE a.design_revision_id = NEW.id
                             AND a.reviewer_type = 'manager'
                             AND a.decision = 'approved'
                       ) THEN
                        RAISE EXCEPTION 'Customer and Manager approvals are required';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        schema_editor.execute(
            f"DROP TRIGGER IF EXISTS core_designrevision_guard ON {table}"
        )
        schema_editor.execute(
            f"CREATE TRIGGER core_designrevision_guard "
            f"BEFORE INSERT OR UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION core_guard_designrevision_mutation()"
        )
        attachment_table = connection.ops.quote_name("core_designrevisionfile")
        schema_editor.execute(
            """
            CREATE OR REPLACE FUNCTION core_guard_designrevisionfile_mutation()
            RETURNS trigger AS $
            BEGIN
                IF TG_OP = 'DELETE' THEN
                    IF EXISTS (SELECT 1 FROM core_designrevision r
                               WHERE r.id = OLD.design_revision_id AND r.locked_at IS NOT NULL) THEN
                        RAISE EXCEPTION 'Files attached to an approved design revision cannot be removed';
                    END IF;
                    RETURN OLD;
                ELSIF TG_OP = 'UPDATE' THEN
                    IF EXISTS (SELECT 1 FROM core_designrevision r
                               WHERE r.id = OLD.design_revision_id AND r.locked_at IS NOT NULL)
                       OR EXISTS (SELECT 1 FROM core_designrevision r
                                  WHERE r.id = NEW.design_revision_id AND r.locked_at IS NOT NULL) THEN
                        RAISE EXCEPTION 'Files attached to an approved design revision are immutable';
                    END IF;
                    RETURN NEW;
                ELSE
                    IF EXISTS (SELECT 1 FROM core_designrevision r
                               WHERE r.id = NEW.design_revision_id AND r.locked_at IS NOT NULL) THEN
                        RAISE EXCEPTION 'Files cannot be attached to an approved design revision';
                    END IF;
                    RETURN NEW;
                END IF;
            END;
            $ LANGUAGE plpgsql;
            """
        )
        schema_editor.execute(
            f"DROP TRIGGER IF EXISTS core_designrevisionfile_guard ON {attachment_table}"
        )
        schema_editor.execute(
            f"CREATE TRIGGER core_designrevisionfile_guard "
            f"BEFORE INSERT OR UPDATE OR DELETE ON {attachment_table} "
            "FOR EACH ROW EXECUTE FUNCTION core_guard_designrevisionfile_mutation()"
        )


def remove_design_revision_guards(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor
    table = connection.ops.quote_name("core_designrevision")

    if vendor == "sqlite":
        schema_editor.execute("DROP TRIGGER IF EXISTS core_designrevision_reject_unapproved_insert")
        schema_editor.execute("DROP TRIGGER IF EXISTS core_designrevision_immutable_update")
        schema_editor.execute("DROP TRIGGER IF EXISTS core_designrevision_immutable_delete")
        schema_editor.execute("DROP TRIGGER IF EXISTS core_designrevision_require_approval_lock")
        schema_editor.execute("DROP TRIGGER IF EXISTS core_designrevisionfile_reject_locked_insert")
        schema_editor.execute("DROP TRIGGER IF EXISTS core_designrevisionfile_reject_locked_update")
        schema_editor.execute("DROP TRIGGER IF EXISTS core_designrevisionfile_reject_locked_delete")
    elif vendor == "postgresql":
        schema_editor.execute(
            f"DROP TRIGGER IF EXISTS core_designrevision_guard ON {table}"
        )
        schema_editor.execute(
            f"DROP TRIGGER IF EXISTS core_designrevisionfile_guard ON {connection.ops.quote_name('core_designrevisionfile')}"
        )
        schema_editor.execute(
            "DROP FUNCTION IF EXISTS core_guard_designrevisionfile_mutation()"
        )
        schema_editor.execute(
            "DROP FUNCTION IF EXISTS core_guard_designrevision_mutation()"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_design_approval_database_guards"),
    ]

    operations = [
        migrations.RunPython(
            install_design_revision_guards,
            reverse_code=remove_design_revision_guards,
        ),
    ]
