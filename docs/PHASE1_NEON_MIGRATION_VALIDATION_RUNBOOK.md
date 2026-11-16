# SADACO Phase 1 — Disposable Neon Migration Validation Runbook

**Purpose:** Validate the exact Django migration graph against the isolated pre-reset Neon clone, not production.

## Target and safety boundary

- Neon project: `silent-hill-58749070`
- Disposable branch: `sadaco-phase1-migration-validation-2026-11-16`
- Branch ID: `br-lucky-pond-azm200bm`
- Database: `neondb`
- Source branch: `feature/phase-2-department-access`
- Do not use the production/default branch (`br-twilight-wave-az5nupxb)), staging branch, or any Render deployment.
- Keep the clone's connection string in a local environment variable or secret manager. Never paste it into chat, commit it, or put it in CI logs.
- Do not use `--fake`, hand-written DDL, direct edits to `django_migrations`, or a manual seed script.

## Pre-migration evidence

The clone's current migration recorder is at accounts 0004, core 0001, staff 0001, sales 0006, products 0009, finance 0002, purchase 0001, inventory 0001, production 0001, quality 0001 and marketing 0001. It also has legacy finance recorder names `0003_finance_management`, `0004_repair_finance_options`, and `0005_force_repair_paymentmethod_table`, which are absent from current source.

Read-only inspection found:
- `finance_financetransaction` has no `supplier_payment_id` and 0 rows.
- `finance_supplierpayment` matches the current 0002 table definition and has 0 rows.
- Legacy `finance_paymentmethod` has 5 rows and no inbound foreign keys. Leave it untouched.
- Protected identity baseline: 9 Users, 9 UserProfiles, 5 StaffProfiles, 5 Designations, 5 WorkAreas and 9 user/group membership rows.

ID fingerprints to compare after the migration:
- Users: `4465827426a5fff877ca7c2b8cc1aab5`
- UserProfiles: `eac5e1a344782c05d087e0f1886cdeca`
- StaffProfiles: `c436b71eac35fe591730a7a4e18d0989`
- User/group membership: `e661300fb53419a755bb1bd700eceb41`

## Execution procedure

Use the exact feature-branch checkout and its pinned dependencies. Confirm `git status` is clean and `git rev-parse --abbrev-ref HEAD` reports the intended branch. Point Django only at the disposable clone.

1. Confirm the target database identity from the connection host/database metadata before running Django.
2. Run a read-only plan first:

   ```bash
   python manage.py check
   python manage.py migrate --plan
   python manage.py showmigrations
   ```

3. Stop if Django reports inconsistent migration history, missing dependencies, duplicate leaves, unexpected operations, or any connection target other than the disposable branch. Capture the complete error; do not repair the database manually.
4. If the plan is coherent and the target is verified as the disposable clone, run the normal migration engine:

   ```bash
   python manage.py migrate --noinput
   python manage.py migrate --check
   ```

5. Run the targeted and full regression suites:

   ```bash
   python manage.py test products.test_pdf_baseline_migrations
   python manage.py test
   ```

6. Inspect the schema and migration recorder read-only. Confirm:
   - current feature migrations are recorded once, including finance 0003 and products 0010–0013;
   - `finance_financetransaction.supplier_payment_id` exists with its unique constraint/index and FK to `finance_supplierpayment`;
   - existing `finance_supplierpayment` columns, FKs and indexes remain valid;
   - the legacy `finance_paymentmethod` table was not altered or dropped;
   - PDF seed counts are 51 MaterialVariants, 51 MaterialRateHistory rows, 5 MachineRates and 4 compensation rows, subject to the pre-existing clone state and migration execution semantics;
   - the protected identity counts and fingerprints above are unchanged.

## Interpretation and limitations

- The fresh-PostgreSQL GitHub Actions run verifies the current source migration chain on a clean database. It is not a substitute for this legacy-clone execution.
- The checked-in `products.0012_remove_demo_operational_data` is catalogue-only cleanup; it does not reproduce the separately authorized full PDF-baseline reset performed on production.
- Do not delete the five-row legacy PaymentMethod table as part of this migration test. Any later archival/removal requires a separate dependency and data-retention review.
- A successful clone test permits a technical review of the migration result; it does not authorize merge to `main`, production schema writes, or Render deployment. Obtain separate explicit approval for release actions.
