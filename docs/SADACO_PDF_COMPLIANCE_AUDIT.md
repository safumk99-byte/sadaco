# SADACO ERP — PDF Compliance Audit & Implementation Tracker

**Authority:** `SADACO_ERP_Final_Requirements_v2.pdf` (11 pages; final source of truth)  
**Working branch:** `feature/phase-2-department-access`  
**Release policy:** Production database baseline reset was explicitly authorized and executed on 2026-11-15; do not make further production writes or deploy/merge to `main` without separate approval.

## Acceptance rules

- The PDF is the business specification; existing code and demo data do not override it.
- The final PDF is the sole source of truth. Legacy ERP operational/catalogue data is not authoritative and may be cleared and rebuilt to match the PDF.
- Preserve all existing authentication/account records (Django Users, UserProfiles, role/group and permission assignments) and all Staff master profiles. Do not delete, recreate, rename or reset their login credentials.
- Legacy Products, prices, orders, stock balances/transactions, customers, quotations, production, purchasing, finance, attendance/task/performance history, notifications and other non-account/non-staff operational data may be cleared where they are outside the final PDF baseline. Rebuild required master/configuration data from the PDF.
- Preserve only staff-linked master data needed to keep the retained Staff profiles valid (for example, referenced designations/work areas); replace or normalize other configuration to the PDF.
- Never invent unspecified prices, tax rates, approval limits, reorder levels, wastage percentages or overhead percentages.
- Destructive cleanup requires explicit user authorization, a before/after identity snapshot and transactional verification. The authorized production baseline reset is documented below; no further production cleanup is authorized by this note.
- Each implementation phase must be testable and reviewable before moving on.

## Current-state gap assessment

Status labels: **Partial** = a basic model/page exists but does not satisfy the full PDF workflow; **Missing** = no complete implementation found in the inspected branch; **Needs verification** = code exists but end-to-end behavior/data is not yet proven.

| PDF area | Current branch evidence | Assessment / required work |
|---|---|---|
| Group/divisions and Founder dashboard (1, 3, 20) | Department model, department-aware APIs, dashboard and reports exist | **Partial** — establish the three named divisions as configured departments; validate consolidated totals and drill-down by division. |
| Roles and department access (2, 21, 42) | UserProfile roles and department scoping exist | **Partial** — audit every API for active-account checks, least privilege, confidential finance/salary access and cross-department isolation. |
| CRM and enquiries (4) | Customer, Enquiry, CustomerInteraction and follow-up fields exist | **Partial** — customer type/location, duplicate detection, follow-up reminders/overdue indicators and full communication history need verification/completion. |
| Quotations (5) | Quotation stores cost components, price, advance and validity | **Partial** — dimensions/material detail, configurable tax, discount authority/approval thresholds, pending-approval workflow and branded itemized PDF need completion. |
| Order lifecycle (6, 22) | SalesOrder and related status APIs exist | **Partial** — enforce the full lifecycle, sequential SAD-YYYY numbering, division, dimensions, advance/balance, approved design, deadlines and approval exceptions. |
| Design management (7) | DesignApproval is versioned and has response statuses | **Partial** — enforce immutable approved versions and revision creation; verify file-type support, review workflow and production gate. |
| Production/job cards (8–9) | ProductionJob, progress, material and issue models exist | **Partial** — add stage-level ownership/timestamps/evidence, actual material/time capture, attachments/photos and employee completion/issue reporting. |
| Material master and rate history (27–32, 41–42) | MaterialVariant, rate history and seeded purchase rates exist | **Partial** — verify every supplied rate against PDF; separate purchase/retail, historical stock valuation and material-to-inventory integration. |
| Inventory/offcuts (10, 37, 41) | Product stock ledger, MaterialIssue, StockCount and ReorderAlert exist | **Partial** — material stock is not unified with MaterialVariant; implement receipts/issues/returns/waste/offcuts, location, minimum levels and traceability to job/employee. |
| Purchasing/suppliers (11, 41) | Supplier, PurchaseOrder, PurchaseItem and GoodsReceipt exist | **Partial** — purchase lines currently reference Product, receipt line quantities/invoices are incomplete; connect material variants, invoice/payables and receipt-to-stock posting. |
| Accounts (12) | Expense, FinanceTransaction and SupplierPayment exist | **Partial** — validate cash/bank/UPI balances, receivables/payables, division profitability, reversals, P&L and no salary double-counting. |
| QC/rework (13) | QualityCheck, ReworkRecord and PackingRecord exist | **Partial** — complete checklist fields/photos and hard-block delivery until final QC pass. |
| Delivery/installation (14) | Delivery APIs and sales delivery records exist | **Needs verification** — enforce specified statuses, contact/address/staff/schedule/photos/customer confirmation and interior site-measurement workflow. |
| HR/attendance/salary (15, 35–36) | Staff, attendance, performance and compensation exist | **Partial** — attendance lacks Late and Half Day; salary seed must match actual verified staff only; implement payment history, work-based payments and office schedule. |
| KPIs, feedback and notifications (16–18) | Performance, feedback, notification and push models/APIs exist | **Partial** — complete KPI definitions, complaint assignment/resolution history and event-specific notification coverage. |
| Product catalogue/multi-division (19–20) | Product and ProductCategory exist | **Partial** — verify catalogue fields and division-specific visibility/performance; retire demo catalogue without deleting referenced operational records. |
| Reports (23, 42) | Reports dashboard API/page exists | **Partial** — build daily/weekly/monthly/annual reports and PDF/Excel exports, including stock valuation, job variance, profitability and receivables/payables. |
| Job costing (27, 32–42) | MaterialVariant, MachineRate, StaffCompensation and MaterialCosting page exist | **Major gap** — no complete job-cost sheet/calculator, material/machine/labour lines, work-time tracking, wastage/offcuts, consumables, overhead allocation, templates, estimate-vs-actual variance or job profit/margin/markup workflow found. |
| Platform, backup and recovery (21, 25–26) | React/Django and cloud database integrations exist | **Needs verification** — responsive/mobile behavior, secure file storage, automated backup/restore, exports, operational documentation and recovery tests. |

## Verified supplied values to preserve

- Currency: INR.
- Astari Acrylic 8×4 ft (32 sq ft): 1.8 mm codes 402/434/136/502 colour ₹3,085; code 441 colour ₹3,160; Others clear ₹2,950 and colour ₹3,050. Clear rates for the named 1.8 mm codes are not supplied.
- Astari thickness rates: 2.5 mm ₹3,812/₹3,864; 2.7 ₹4,368/₹4,440; 3.5 ₹4,960/₹5,152; 3.7 ₹5,529/₹5,920; 4.5 ₹6,200/₹6,340; 4.8 ₹7,040/₹7,400; 5.5 ₹7,622/₹7,728; 5.8 ₹8,448/₹8,880; 6.8 ₹9,856/₹10,360; 7.8 ₹11,264/₹11,840 (clear/colour).
- Astari 6.5 mm and 7.5 mm: unavailable; do not seed as zero.
- Otherbrand Acrylic 8×4 ft: 2 mm ₹2,550/₹2,650; 3 mm ₹3,552/₹3,648; 4 mm ₹4,736/₹4,864; 5 mm ₹5,920/₹6,080; 6 mm ₹7,104/₹7,296; 7 mm ₹8,288/₹8,512; 8 mm ₹9,472/₹9,728 (clear/colour).
- Indian Sheet 4×3 ft: 2 mm ₹455; 3 mm ₹560; 4 mm ₹796; 5 mm ₹1,060; 6 mm ₹1,200. Retail rates blank.
- Mirror Sheet 8×4 ft: Gold/Silver Gum ₹1,980; Rose/Copper Gum ₹2,100; 2 mm Gold/Silver ₹2,200; 3 mm Gold/Silver ₹2,900; Brush Gold/Silver ₹640. Retail rates blank.
- Laser cutting ₹20/min; engraving ₹25/min.
- CNC Multy Wood: 5 mm ₹50/sq ft; 6 mm ₹50/sq ft; 8 mm ₹60/sq ft.
- Monthly salaries: Manager ₹25,000; Muhaimin ₹15,000; Junaid ₹11,000; Ashiq ₹10,000 (total ₹61,000). Shibili and Sakeer are work-based; their rates are not supplied.
- Office: 10:00–20:00; productive time 8.25 hours/day; 26 working days/month; 214.5 hours/month. Sunday weekly holiday.
- No assumed retail prices, work-based rates, additional machine/material rates, consumable rates, packing/delivery rates, reorder levels, wastage percentage or overhead percentage.

## Implementation sequence

1. **Foundation and data safety:** reconcile Django migration history with Neon; validate role/department security; protect operational references in demo cleanup.
2. **Core workflow completion:** CRM, quotation approval, order lifecycle, design locking/revisions, production stage/job cards.
3. **Factory data model:** unify material master with inventory; purchase receipts, issues/returns, offcuts/waste and stock valuation.
4. **Complete costing engine:** job-cost sheet, material/machine/labour/other lines, time tracking, templates, overhead configuration, estimate-vs-actual and profit/margin/markup.
5. **Quality, delivery and finance gates:** QC checklist/rework, delivery blocking, payment/credit approvals, accounts and reversals.
6. **HR, notifications, KPIs and reporting:** attendance statuses, work-based pay, dashboards, period reports, PDF/Excel exports.
7. **Acceptance:** migrations on staging, automated tests, frontend build, workflow tests, permission tests, restore verification and user review before production release.

## Current execution notes

- Costing, production, sales, quality, purchasing, finance, reports and delivery privileged-data helpers now require an active UserProfile (superusers remain supported). A costing regression test covers inactive managers.
- Demo catalogue cleanup migration was narrowed and further guarded against customer-request, purchase, production, stock-count, reorder and stock-ledger references.
- Latest CI status is recorded in the dated execution notes below. Neon staging migration has not been run. `main` and Render deployment remain untouched.


## 2026-11-15 staging migration reconciliation finding

Read-only inspection of Neon staging branch `sadaco-reconciliation-staging` (`br-shiny-bread-azhv8lcr`) confirms that its migration history is not the history expected by the current feature branch:

- Staging records finance migrations `0001_initial`, `0002_accounts_control_center`, `0003_finance_management`, `0004_repair_finance_options`, and `0005_force_repair_paymentmethod_table`.
- Feature branch instead contains `finance.0001_initial`, `0002_accounts_control_center`, and `0003_financetransaction_supplier_payment`.
- Staging has `finance_supplierpayment`, but `finance_financetransaction` has no `supplier_payment_id` column. The feature branch's 0003 migration expects to add that OneToOne field.
- Staging also lacks the later feature-branch migrations `accounts.0005_userprofile_department`, `core.0002_department`, `staff.0002_staffprofile_department`, and `sales.0007_customer_department`; these are relevant to department scoping.
- This is a migration-history/schema divergence, not proof that staging data is disposable. No migration, fake migration, schema alteration, or data update was executed.

**Required safe resolution:** compare the complete historical migration files and live table definitions for every affected app; map the deployed staging schema to the current model state; then create an explicit, forward-only reconciliation plan and test it against a fresh disposable clone before applying any staging migration. Do not run `migrate`, `--fake`, or hand-written DDL against staging or production until this plan is reviewed and validated.



Additional read-only schema check on the same staging branch:

- `accounts_userprofile`, `staff_staffprofile`, `sales_customer`, `sales_enquiry`, `sales_quotation`, and `sales_salesorder` currently have no `department_id` column.
- `core_department` is not present in the inspected schema.
- This confirms the department migrations recorded as pending on the feature branch have not been applied to staging. Because the staging migration history also differs from the branch history, do not simply apply those pending migrations until the migration graph and table state are reconciled.


## Reconciliation decision — do not auto-bridge unknown historical migrations

A full read-only `django_migrations` listing shows the staging branch records only the old migration names for the affected applications (including finance 0003–0005), while those migration source files are absent from both the current feature branch and the current `main` branch. The live schema confirms the old finance shape (`finance_financetransaction.sales_payment_id`, no `supplier_payment_id`) and the absence of department tables/columns.

Consequently, a simple migration rename, dependency edit, or `--fake` operation is not safe: Django's migration graph cannot infer the operations performed by missing historical files. Keep the current feature branch migrations unchanged until a verified schema reconciliation is designed. The next safe engineering step is to produce a disposable staging clone and compare all affected app tables, constraints, indexes, sequences, and row counts against the current model state; only then create a guarded reconciliation migration using explicit schema introspection and a state transition that is tested on the clone. If a disposable clone cannot be provisioned, pause DB migration work rather than guessing.

No SQL writes were run during this investigation. All staging queries were SELECT-only.


## 2026-11-15 stock-preservation regression found before cleanup migration

A read-only query on the disposable staging clone found two legacy product rows with positive stock balances but no stock-ledger rows or other operational foreign-key references:

- `ACR-2IN-BLK` — 10 Sheets, legacy cost ₹495.
- `ACR-3IN` — 10 Sheets, legacy cost ₹595.

The previous `products.0012_remove_demo_operational_data` queryset would have treated these as removable demo catalogue rows because it guarded stock transactions and foreign-key references but did not guard a non-zero `Product.stock_quantity`. This would have silently deleted 20 sheets of recorded stock.

**Correction committed:** the cleanup queryset now excludes products with `stock_quantity > 0`. These two rows are preserved; their old rates are not treated as authoritative because they conflict with the final PDF. They must be reconciled against a physical stock count and the approved material master before any conversion or adjustment. No stock was changed.

The same clone confirms 25 product rows total, 2 with positive stock, 0 referenced by purchase items, production materials, stock counts, stock transactions or customer order requests. The 3 customer order requests themselves remain untouched.

## Staging clone: material and staff baseline

- The staging-derived clone has no `products_materialvariant` table because `products.0010_material_master_and_costing_rates` has not been applied there. The material master and PDF-approved rate seed are present in feature-branch source only, not yet in staging schema.
- The 5 existing staff profiles are Abdul Bsaith (Manager), Muhammed Rabeeh (Sales Executive), Muhammed Shibili, Sakkeer T, and Abdul Muhaimin. The PDF salary seed can safely match the Manager and Muhaimin by existing account, and Shibili/Sakkeer as work-based; no Junaid or Ashiq staff profiles exist and no profiles should be fabricated.
- The old product catalogue contains legacy rates that differ from the final PDF. Use the separate `MaterialVariant` master from migration 0010 as the authoritative rate source after safe migration reconciliation; do not silently copy legacy Product.cost_price values into it.


## 2026-11-15 final legacy-data decision

The user has explicitly superseded the earlier conservative operational-data preservation rule:

- The final requirements PDF is the sole source of truth.\n- Legacy operational/catalogue data may be fully removed and rebuilt; do not preserve old demo products, old rates, orders, stock, customer records or old workflow history merely because they exist.
- **Mandatory preservation boundary:** retain every existing Django User/account, UserProfile, authentication credential, role/group/permission assignment, and every existing StaffProfile. Never delete or recreate these identities.
- Retain only staff-linked designation/work-area master rows required by retained staff foreign keys; all other legacy business data/configuration is eligible for cleanup and PDF-based reseeding.
- Before any cleanup, generate a table-by-table deletion plan and verify that cascades cannot delete Users, UserProfiles or StaffProfiles. Apply and test only on the isolated disposable/staging clone first. Do not touch production Neon or the main branch.
- This decision supersedes the earlier notes about preserving customers, order requests, nonzero stock, and referenced operational records. Those records are no longer preservation requirements.


## 2026-11-15 guarded PDF-baseline cleanup implementation

Added `core/management/commands/reset_to_pdf_baseline.py` on the feature branch.

- Default invocation is **dry-run**; it prints a deletion graph/count by model and performs no writes.
- `--apply` is required to delete legacy operational rows.
- Explicitly preserves Django User accounts, Groups, Permissions, ContentTypes, UserProfiles, StaffProfiles, Departments, staff Designation/WorkArea master rows, PDF MaterialVariants/rate history, MachineRates and StaffCompensation.
- The command uses Django's deletion collector to calculate cascades before deleting. If the collector reaches a protected model, it stops.
- Cleanup runs in a database transaction and checks that User, UserProfile and StaffProfile row counts are unchanged; a mismatch raises and rolls back.
- Old Products/prices/orders/stock/purchasing/finance/production/sales/QC/delivery/marketing/attendance/task/notification and other eligible legacy business rows are included in the cleanup scope.
- This command was not used for the actual Neon cleanup; the authorized production and disposable-clone resets were performed through explicit SQL transactions with independent protected-identity verification. Keep the command dry-run by default; do not assume its execution reproduces the complete SQL reset.
- The old notes above about preserving customers, order requests and nonzero legacy stock are superseded by the user's final decision. Only the explicit protected models above remain preservation requirements.


## 2026-11-15 disposable clone cleanup and PDF baseline seed — executed

Target: Neon branch `sadaco-schema-reconciliation-test` (`br-round-scene-az7j6wqc`) only. This is a disposable child branch; the production/default branch and the separate staging branch were not targeted.

- CI run #106 for commit `5021b07e87991e0cf81d324da62bf35378a5195e` completed successfully: Django tests and frontend build both passed.
- Executed the legacy-data cleanup in one database transaction. The protected-record snapshot check initially detected a false mismatch due to a verification-query construction issue; the transaction rolled back. The corrected bidirectional snapshot comparison then passed and committed the cleanup.
- Verified post-cleanup: Products 0, Product Categories 0, Customers 0, Order Requests 0; all inspected operational tables are empty.
- Verified preserved identity: 9 auth users, 9 UserProfiles, 5 StaffProfiles, 5 Designations, 5 WorkAreas. User/group/permission membership and content-type snapshots matched before/after cleanup.
- Created and seeded 3 Departments; added nullable department foreign keys to UserProfile, StaffProfile and Customer.
- Created MaterialVariant, MaterialRateHistory, MachineRate and StaffCompensation tables; added FinanceTransaction.supplier_payment_id.
- Seeded 51 material variants and 51 initial rate-history rows from the approved PDF, 5 machine rates, and 4 compensation records for existing staff only.
- Compensation records: Manager ₹25,000/month; Abdul Muhaimin ₹15,000/month; Shibili and Sakkeer work-based with no invented rates. The currently seedable monthly salary total is ₹40,000 because Junaid and Ashiq do not have StaffProfile records; no synthetic staff identities were created. The PDF's ₹61,000 full salary plan remains documented for when those staff profiles are legitimately added.
- Verified feature migration names are present in `django_migrations` for the schema changes represented in this reconciliation: core 0002, accounts 0005, staff 0002, sales 0007, products 0010–0013, and finance 0003.
- Neon schema diff against the clone's parent confirms the expected department/material/compensation/supplier-payment tables and columns were added. The clone still carries older staging-only finance migration records and an extra legacy PaymentMethod table; these are not silently removed.

**Important implementation note:** because the clone's recorded migration history diverged from the feature branch (including staging-only finance 0003–0005 names), the schema reconciliation was applied as an explicit transactional DDL/data operation on this disposable clone, and the corresponding feature migration records were added after the schema/data operations. This was not a normal Django `migrate` invocation. Do not repeat this procedure on staging or production. Before any production release, reconcile the historical finance migration graph cleanly in source control and test a fresh clone from the intended deployment baseline.

At the time of this disposable-clone entry, production Neon and `main` remained untouched. A later, separately authorized production baseline reset is documented below.


## 2026-11-15 production PDF-baseline reset — executed with user authorization

**Target:** Neon production/default branch `br-twilight-wave-az5nupxb`, database `neondb`. This operation was explicitly authorized by the user. It was executed in a single SQL transaction; it was not run through Django's `migrate` command.

- A pre-reset Neon branch snapshot was created: `sadaco-production-pre-reset-backup-2026-11-15` (`br-weathered-star-azd003a6`). The backup branch was created with compute disabled; a SQL restore/query test against that branch has not been completed.
- Cleared legacy/demo operational data and catalogue/workflow rows covered by the approved reset. Post-reset verification across 43 operational tables returned zero rows in every checked table.
- Preserved account and staff identities: 9 Django Users, 9 UserProfiles, 5 StaffProfiles, 5 Designations and 5 WorkAreas. Existing credentials, role/group/permission assignments and staff identities were outside the cleanup target.
- Created 3 departments (SADACO Creatives, SADACO CNC, SADACO Decor Co.) and nullable department references on UserProfile, StaffProfile and Customer.
- Created material/costing tables and seeded 51 MaterialVariants, 51 initial MaterialRateHistory rows, 5 MachineRates and 4 StaffCompensation rows.
- Existing staff compensation: Manager ₹25,000/month; Abdul Muhaimin ₹15,000/month; Shibili and Sakkeer work-based with no invented rates. Seedable monthly salary total is ₹40,000. Junaid ₹11,000 and Ashiq ₹10,000 remain unassigned because no matching StaffProfile records exist; no synthetic staff identities were created.
- Added `FinanceTransaction.supplier_payment_id`; recorded the feature migration names in `django_migrations` for the manually reconciled schema changes.
- A post-reset read-only verification on production reconfirmed all nine expected migration records, the department foreign-key columns, the material/rate/machine/compensation counts, and the preserved identity counts.

**Critical migration caveat:** this production schema/data reconciliation was applied with explicit transactional SQL and migration records were then inserted. It was **not** a normal Django `migrate` execution. The branch migration graph has a known historical divergence from Neon staging, particularly in the finance app. Do not blindly run `migrate`, `--fake`, or the feature migration chain against staging or production. Before deployment, reconcile the complete migration graph and test it against a fresh disposable clone.

## Latest source/CI verification — 2026-11-15

- Feature branch latest commit at review time: `ada2efc9d804985fa6505229d0c22f70c925bc22`.
- GitHub Actions run #107 (ID `43719936992`) for that exact commit completed successfully. Run URL: https://github.com/safumk99-byte/sadaco/actions/runs/43719936992
- This supersedes the earlier run #106 reference for the current feature-branch tip. CI success does not establish production deployment or end-to-end acceptance against the reset database.
- Read-only production inspection confirms:
  - `core_department`: 3 rows
  - `products_materialvariant`: 51 rows
  - `products_materialratehistory`: 51 rows
  - `products_machinerate`: 5 rows
  - `products_staffcompensation`: 4 rows
  - `auth_user` / `accounts_userprofile`: 9 / 9 rows
  - `staff_staffprofile`: 5 rows
  - expected department/supplier-payment/working-hours columns are present
- `main`, Render deployment and staging branch remain untouched.

## Immediate engineering findings / release blockers

1. **Migration history reconciliation remains a release blocker.** Production schema was reconciled manually and migration records were inserted; this does not prove that a clean deployment from the feature branch can reproduce the same schema.
2. **Cleanup behavior differs between paths.** The SQL reset cleared the broader operational baseline. The checked-in `products.0012_remove_demo_operational_data` migration only removes eligible Product/ProductCategory catalogue rows; it does not reproduce the full operational-table reset. Keep this distinction explicit and do not infer that applying 0012 performs the production reset.
3. **UI readiness is not established.** The database has the PDF master data, but the currently deployed application has not been promoted/tested against this schema. Do not represent the live UI as fully updated.
4. **Do not fabricate missing staff identities or rates.** Junaid/Ashiq salary entries require legitimate StaffProfile records; work-based compensation rates and unspecified cost inputs remain blank until supplied.
5. **Next release-safe sequence:** finish migration-graph reconciliation in source control; create a fresh disposable branch from the intended deployment baseline; run normal `python manage.py migrate`; verify model/schema parity and seed idempotence; run backend/frontend/Playwright and role-isolation tests; test backup restoration; then request explicit user approval before merge/deploy.


## 2026-11-15 production-backup migration baseline inspection

A new isolated test branch was created from the pre-reset production snapshot, not from staging and not from the live production branch:

- Branch: `sadaco-prod-migration-reconciliation-test-2026-11-15`
- Neon branch ID: `br-silent-recipe-az41w09q`
- Parent: pre-reset snapshot `br-weathered-star-azd003a6`
- The test branch is ready and has its own read-write compute. No SQL writes or Django migrations have been run on it yet.

Read-only inspection confirms the pre-reset production migration history differs from staging in the same important way:

- Accounts has migrations 0001–0004; core has 0001; staff has 0001; sales has 0001–0006; products has 0001–0009.
- Finance has 0001 and 0002 from the current feature branch **and** legacy applied records named `0003_finance_management`, `0004_repair_finance_options`, and `0005_force_repair_paymentmethod_table`. Those three legacy migration source files are absent from the current feature branch.
- The legacy finance transaction table has the expected base fields, including `sales_payment_id`, and does not yet have `supplier_payment_id`. The SupplierPayment table already exists and has its purchase-order and payment fields.
- The clone contains 9 users, 9 UserProfiles, 5 StaffProfiles, 3 customers and 25 legacy Products at the snapshot point. This is the untouched pre-reset dataset; do not confuse it with the live production baseline.

The current feature migration `finance.0003_financetransaction_supplier_payment` depends on the known current `finance.0002_accounts_control_center` and adds the missing nullable OneToOne field. The existence of old, unknown migration records alone does not prove a graph conflict: Django generally evaluates dependencies for migration nodes present in the loaded graph. However, the full legacy finance table/index/constraint state still needs runtime validation against the current migration/model state before this is declared safe.

The current CI run #108 for commit `4a1107ec683035f970835d77fbb7e868c0a7e389` completed successfully:
- `django-tests`: success
- `frontend-build`: success
- CI applies the complete migration chain to a fresh PostgreSQL 16 database and runs the listed regression tests. It does **not** connect to the Neon backup clone, so it is not a substitute for the legacy-baseline migration test.

**Remaining verification:** execute `python manage.py migrate --plan`, `python manage.py migrate --noinput`, and `python manage.py migrate --check` using the exact feature-branch code and the isolated Neon test branch; then compare every affected table, constraint, index, sequence and row count. Do not run this test against production. The migration test has not yet been executed; no success is claimed.


## 2026-11-15 — Department API isolation follow-up

- Restricted `products/costing_api.py` staff compensation reads and writes to active staff in the requesting manager's own department. Superusers and global administrators retain cross-department access.
- Finance API review: sales receipts are scoped through the linked sales order's customer department; supplier payments are scoped through their linked purchase order; expense records are scoped through the creator's department. No Finance API changes were made in this pass.
- Purchase API review: purchase orders are scoped by the creator's department. Supplier and product records are shared master data in the current schema; no division ownership field exists for either. They remain shared rather than imposing a misleading division filter.
- Material variants and machine rates are currently global shared rate masters. Staff compensation is now department-scoped; do not assume material/machine rates should be duplicated per division without a business rule.
- Inventory products and stock are also global in the current schema. True division-level inventory isolation requires an explicit ownership/stock-location data model and migration; filtering by creator would be incorrect for shared stock.
- Verification limitation: GitHub commit status for the compensation-scope commit has not yet reported CI checks. No production database writes, merge to `main`, or Render deployment were performed.


## 2026-11-16 — Phase 1 PDF seed-source audit (read-only)

Reviewed the current feature-branch seed migrations against the verified PDF values in this tracker and the retained staff identities on the isolated pre-reset validation clone.

- The `products.0010_material_master_and_costing_rates` seed defines 51 MaterialVariant rows by composition: 7 Astari 1.8 mm variants, 20 other Astari thickness/colour variants, 14 Otherbrand acrylic variants, 5 Indian Sheet variants, and 5 Mirror Sheet variants. The supplied purchase rates and sheet dimensions match the verified values above; retail rates remain blank where the PDF supplies none. Astari 6.5 mm and 7.5 mm are not seeded.
- The same migration defines exactly 5 MachineRate rows: laser cutting ₹20/min, laser engraving ₹25/min, and CNC Multy Wood 5/6/8 mm at ₹50/₹50/₹60 per sq ft. These match the verified PDF values.
- The existing retained staff identities on the isolated legacy clone are `abdulbasith` (Abdul Bsaith), `rabeeh`, `shibili`, `sakkeer`, and `abdulmuhaimin`. The current `0011_seed_staff_compensation` matching logic maps the Manager to ₹25,000/month, Muhaimin to ₹15,000/month, and Shibili/Sakkeer to work-based compensation without inventing rates. Rabeeh receives no compensation record from this seed. Junaid and Ashiq have no retained StaffProfile in this clone and are not fabricated; the full ₹61,000 salary plan is therefore not yet assignable.
- The `core.0002_department` seed uses `get_or_create` keyed by stable department codes for the three named divisions.
- No source-code changes, database writes, migration runs, or production operations were performed in this audit. This confirms the source definitions only; it does not prove the migrations execute successfully against the clone.

**Remaining blockers:**

1. The actual Django migration engine still must run `migrate --plan`, `migrate --noinput`, and `migrate --check` against `br-lucky-pond-azm200bm` using the exact feature-branch checkout. The Mobile Commander PC Bridge timed out during this session, so this could not be executed.\n2. Add automated migration/seed assertions for 51 material variants, 51 initial rate-history rows, 5 machine rates, the expected staff compensation mapping and the 3 department codes. Current inspection found no dedicated tests for these migration seed expectations in `products/tests.py`.
3. Verify model/schema parity, indexes, constraints, foreign keys and row counts after the normal Django migration run. Do not substitute hand-written DDL or manual migration-record insertion.
4. Do not run the broad PDF-baseline cleanup migration as if it reproduced the authorized operational reset. The checked-in `products.0012_remove_demo_operational_data` is catalogue-only and intentionally preserves multiple legacy business relations; the broader reset was a separate, explicitly authorized transaction already recorded above.

Production, `main`, Render deployment and the disposable validation clone remain unchanged by this read-only audit.


## 2026-11-16 — Phase 1 migration-test design review (read-only)

A second source review focused on the seed migration behavior and the current test coverage:

- `products/tests.py` currently tests product forms, access to product pages and stock-ledger operations. It does not assert the PDF seed migration outputs or exercise the historical migration state.
- `products.0010_material_master_and_costing_rates` uses historical models from the migration app registry (correct for a data migration), seeds MaterialVariant and MachineRate rows, and records an initial MaterialRateHistory row for each priced material. Its reverse data operation is intentionally a no-op; the table-creation operations are reversed by Django separately.
- `products.0011_seed_staff_compensation` only iterates existing StaffProfile rows. It does not create missing staff identities. The matching logic therefore cannot assign Junaid/Ashiq until legitimate StaffProfile records exist. This is consistent with the identity-preservation rule, but the ₹21,000 unassigned portion must remain visible as a configuration gap rather than be silently treated as payroll-ready.
- `MaterialRateHistory` has no uniqueness constraint on (material, effective_from), and `MachineRate` has no uniqueness constraint on its natural key (operation, material_name, thickness_mm). This is not proof of a current duplicate, and no constraint should be added without confirming the intended business semantics (multiple same-day rate changes may be legitimate). It does mean tests should verify exact seeded row counts and should detect duplicate natural-key machine rates.
- The current seed uses `update_or_create` for MaterialVariant/MachineRate and `get_or_create` for daily rate history. The migration is designed to run once under Django's migration recorder; it must not be manually re-executed as an ad-hoc seed command. Runtime behavior against the legacy clone remains unverified.
- `core.0002_department` uses stable department codes with `get_or_create`; tests should assert all three exact codes/names and that pre-existing department rows are not overwritten by the seed defaults.

**Test implementation decision:** do not add a test that blindly rewinds the entire live migration graph from a normal test database. The migration graph includes cross-app dependencies and a catalogue-cleanup RunPython operation. Implement the migration test with Django's `MigrationExecutor` in a dedicated `TransactionTestCase`, pin the pre-seed historical state, restore the latest leaf migrations in teardown, and run it in CI on disposable PostgreSQL. Then add ordinary model-level tests for rate-history recording and machine-rate natural-key validation if/when the corresponding business constraints are approved. These tests have not yet been implemented or executed.

No application source, migration, database, production, `main`, or Render changes were made in this review.


## 2026-11-16 — Phase 1 PDF seed regression tests added (not yet executed)

- Added `products/test_pdf_baseline_migrations.py` on `feature/phase-2-department-access`.
- The tests cover the exact 51 material variants, 51 rate-history rows, 5 machine rates, representative PDF prices, blank retail rates, absent Astari 6.5/7.5 mm rows, and idempotent material/machine seeding.
- Department seed assertions cover the three exact division codes/names and idempotence.
- Compensation seed assertions verify that only existing StaffProfile records receive compensation, expected monthly/work-based classifications are used, and Junaid/Ashiq identities are not fabricated.
- Capacity defaults are asserted as 26 working days, 8.25 productive hours/day and 214.5 productive hours/month. The test database's normal setup must apply the complete migration graph, including migration 0013.
- These tests call the migration RunPython functions against the test database's current app registry; they are seed-function regression tests, not a historical-state MigrationExecutor test. A dedicated legacy migration-graph test remains outstanding.
- No test command has been run in this session because the PC/local Django environment is unavailable. GitHub commit status currently reports no checks for the test commit; do not describe the tests as passing.
- No Neon branch, production database, `main`, or Render deployment was changed.


## 2026-11-16 — Duplicate products migration leaf resolved in source

- CI run #194 (`4f9c824b80061b15a3ee86ed34cdc7da4f9dd3c6`) confirmed Django's system check and the React frontend build passed, but the Django migration step failed before tests ran.
- The exact error was two `products` leaf nodes: `0013_configurable_labour_hours` and `0013_staff_compensation_working_capacity`.
- Read-only source comparison showed both files had the same dependency (`products.0012_remove_demo_operational_data`) and the same two AddField operations with identical defaults: 26 working days/month and 8.25 productive hours/day. They were duplicate migrations, not independent schema changes.
- Kept the pre-existing canonical migration `products.0013_configurable_labour_hours.py` and deleted the duplicate `products.0013_staff_compensation_working_capacity.py` from the feature branch. Updated the regression-test module docstring to name the retained migration.
- Source-only correction commits: duplicate removal `7e6522ce3267eda675c6395da56678dfd0bb75e8`; test documentation clarification `821d2a684df62679798a0ba961223283b01de1c2`.
- CI has not yet rerun on the corrected head. Do not claim migration or Django regression tests pass until the new run completes.
- No Neon branch, production database, `main`, or Render deployment was changed.

## 2026-11-16 — Corrected migration graph CI verification

- Latest reviewed feature-branch head: `1f83ca9ce2cfb36e935551639bf64c67b3e2fe8f`.
- GitHub Actions run #197 (ID `43785677007`) completed successfully: frontend build, Django system checks, committed database migrations, migration-plan verification, and Django security/business regression tests all passed.
- This run confirms the duplicate `products` migration leaf was resolved and the committed feature-branch migration chain applies successfully to the CI PostgreSQL 16 database.
- The CI regression suite includes `products/test_pdf_baseline_migrations.py`; therefore its seed-function assertions have now executed in CI. These are not historical-state `MigrationExecutor` tests and do not validate the legacy Neon migration history.
- No CI step connected to Neon. The actual Django migration engine has still not been run against isolated Neon validation branch `br-lucky-pond-azm200bm` because the PC/local Django environment is unavailable. The legacy finance-history/schema reconciliation remains the Phase 1 release blocker.
- Next safe work: design a read-only schema/migration-history comparison and a dedicated `MigrationExecutor` test strategy for the legacy baseline. Do not alter migration dependencies, fake migrations, run manual DDL, or write to Neon until that evidence is available.
- Production Neon, `main`, Render and the isolated validation clone remain unchanged by this CI run.


## 2026-11-16 — Isolated legacy-clone migration-history and Finance schema review (read-only)

Target: `sadaco-phase1-migration-validation-2026-11-16` (`br-lucky-pond-azm200bm`), cloned from the pre-reset production snapshot. All queries in this review were SELECT-only.

### Applied migration inventory compared with current source

- The clone has the current source migration history through accounts 0004, core 0001, staff 0001, sales 0006, products 0009, finance 0002, purchase 0001, inventory 0001, production 0001, and quality/marketing 0001.
- The expected current branch migrations after those points are pending: accounts 0005, core 0002, staff 0002, sales 0007, products 0010–0013, finance 0003, purchase 0002–0004, inventory 0002–0005 and production 0002.
- Finance additionally contains three applied recorder names not present in current source: `0003_finance_management`, `0004_repair_finance_options`, and `0005_force_repair_paymentmethod_table`.
- The current source has only finance migrations 0001–0003. Django's migration graph is built from source files; unknown recorder rows do not by themselves prove a dependency conflict. The exact runtime result must still be obtained from the Django MigrationLoader/MigrationExecutor against this clone. Do not rename or fabricate the missing legacy migration files based only on recorder names.

### Finance schema facts

- `finance_financetransaction` matches the current 0001 base columns and current model fields except the not-yet-added nullable `supplier_payment_id`. It currently has 0 rows.
- `finance_supplierpayment` exists with the fields, foreign keys, unique payment number, and two composite indexes defined by current `finance.0002_accounts_control_center`. It currently has 0 rows.
- The current `finance.0003_financetransaction_supplier_payment` adds a nullable OneToOne FK to SupplierPayment and then links matching transaction references. On the inspected clone the data backfill would encounter zero FinanceTransaction and zero SupplierPayment rows; this is an observation, not an execution.
- Legacy `finance_paymentmethod` exists with 5 rows and no referencing foreign-key constraints. It is not represented in the current Finance models. Leave it untouched during migration validation; whether it should eventually be archived/dropped is a separate reviewed cleanup decision.
- FinanceTransaction has the expected current base indexes and foreign keys. No `supplier_payment_id` index/FK/unique constraint exists yet, as expected before current 0003.

### Revised assessment

The read-only evidence does not show a concrete Finance schema collision with current 0003: the target SupplierPayment table exists in the expected shape, the new FinanceTransaction field is absent, and both related tables are empty. The three unknown legacy recorder names and the extra PaymentMethod table remain compatibility items to document, not grounds to alter the migration graph speculatively.

**Still required before calling Phase 1 migration validation complete:** execute `python manage.py migrate --plan`, then the normal `python manage.py migrate --noinput`, then `python manage.py migrate --check` with the exact feature-branch checkout against this disposable clone; inspect the resulting constraints/indexes/schema and compare preserved account/staff identities. The connected GitHub CI run is against fresh PostgreSQL, not this Neon clone. No migration or SQL write was run here. Production, `main`, Render, staging and the validation clone remain unchanged.


### Pre-migration protected-identity baseline captured on validation clone

Read-only counts captured before any Django migration run:

| Relation | Rows |
|---|---:|
| `auth_user` | 9 |
| `accounts_userprofile` | 9 |
| `staff_staffprofile` | 5 |
| `staff_designation` | 5 |
| `staff_workarea` | 5 |
| `auth_user_groups` | 9 |
| `auth_user_user_permissions` | 0 |
| `auth_group_permissions` | 0 |

ID/membership fingerprints for before/after comparison (not credentials or personal data):

- User IDs: `4465827426a5fff877ca7c2b8cc1aab5`
- UserProfile IDs: `eac5e1a344782c05d087e0f1886cdeca`
- StaffProfile IDs: `c436b71eac35fe591730a7a4e18d0989`
- User-to-group membership pairs: `e661300fb53419a755bb1bd700eceb41`

These values are the validation clone's pre-migration comparison baseline. They are not evidence of a migration run; compare them only after a later approved test execution on this disposable branch.


## 2026-11-16 — Phase 3 material/inventory source review (read-only; PC unavailable)

Reviewed the current feature-branch model and service source for `products`, `purchase`, `inventory` and `production`. This was a source inspection only; no application code, migration, database or deployment was changed.

### Confirmed source structure

- `MaterialVariant` is the shared material/rate master. It still contains a legacy/global `stock_quantity` field.
- The newer inventory ledger is department/location scoped through `MaterialStockBalance(material, department, location)`, with `MaterialStockMovement` rows recording balance-after snapshots.
- `MaterialStockLot` ties a received purchase line to a department/location balance and retains original/remaining quantity plus unit cost.
- `PurchaseItem` can reference either a legacy `Product` or a `MaterialVariant`; both foreign keys are nullable.
- `GoodsReceiptLine` records received quantity and unit cost and has an optional one-to-one link to a stock movement. A receipt line can also have one cost lot.
- `ProductionMaterial` supports both legacy Product and new MaterialVariant references. `MaterialIssue` can retain the selected receipt lot, unit rate and stock movement.
- `ReusableOffcut` records material, department, location, dimensions, usable area, source job and status.
- The material movement service uses a database transaction and row-locks the selected balance before changing its quantity. Material issue/return/wastage functions also use atomic transactions and validate department, location, selected receipt lot and per-issue accounting.

### Integration risks requiring endpoint-level verification

1. **Two stock representations:** `MaterialVariant.stock_quantity` remains alongside the authoritative-looking department/location balances. The reviewed `record_material_movement` updates `MaterialStockBalance.quantity` but does not update `MaterialVariant.stock_quantity`. Do not assume these values are synchronized or display the legacy field as current on-hand stock. Search all reads/writes and decide one canonical read model before changing behavior.
2. **Purchase line integrity:** `PurchaseItem.product` and `PurchaseItem.material_variant` are both nullable and no model constraint in the reviewed file enforces exactly one reference. Verify create/update APIs reject both-empty and both-populated lines, and that quantity/rate snapshots use the correct material type.
3. **Receipt posting integrity:** verify the receipt workflow atomically validates that cumulative received quantity cannot exceed the ordered quantity, creates exactly one receipt line per purchase item per receipt, updates the correct department/location balance, creates one matching cost lot, and records one movement. The model has a uniqueness constraint on (receipt, purchase_item) and one-to-one receipt-line links, but those alone do not prove the full posting workflow.
4. **Issue/lot reconciliation:** verify all issue, return and wastage endpoints enforce that lot remaining quantity, balance quantity, issue returned/wastage totals and ProductionMaterial issued/returned/wastage totals reconcile after concurrent requests and retries. The service layer contains row locks and atomic blocks, but endpoint coverage and concurrency tests were not established by this source review.
5. **Offcut lifecycle:** the model records offcut status and dimensions, but the reviewed source does not establish that offcut creation/use/discard is linked to matching stock movements or prevents double use. Verify this before treating offcut area as available inventory or a costing credit.
6. **Department ownership:** balances are department/location scoped and issue logic derives the department from the order customer's department. Verify order/customer department cannot be changed after material issue without a controlled transfer/reversal, and that purchase receipt department is explicitly authorized rather than inferred from the current user.

### Next safe implementation order

- First trace all API/view entry points for purchase order lines, goods receipt posting, material issue, return, wastage, offcut use/discard and stock-count approval.
- Add focused service/API regression tests for the invariants above, including transaction rollback, duplicate submissions, over-receipt, over-issue, wrong-department stock and concurrent balance changes.
- Only after the tests expose a specific defect should a narrowly scoped code change and migration be prepared. Do not add uniqueness or check constraints until existing data and intended business rules are verified.
- Keep `MaterialVariant.stock_quantity` as a legacy field until all references are inventoried; do not bulk-sync or reset it speculatively.

No test command or Django migration was run because the PC/local Django environment is unavailable. The isolated Neon validation clone, production database, `main` and Render remain unchanged.


## 2026-11-16 — Purchase/Inventory/Production API trace (read-only)

Inspected `purchase/api.py`, `purchase/forms.py`, `inventory/api.py`, `inventory/services.py`, `production/api.py`, their API route maps, and the existing purchase/inventory/production test modules on the feature branch. No application code or database was changed.

### Positive controls confirmed in source/tests

- PurchaseItem form validation rejects both-empty and both-selected Product/MaterialVariant references. This addresses the exact-one-reference gap at the API form layer, although the database schema itself does not enforce it.
- Purchase receipt runs inside `transaction.atomic`, locks the PurchaseOrder row with `select_for_update`, and rejects Draft, Cancelled and already-Received orders.
- Material receipt writes a department/location balance movement, GoodsReceiptLine and MaterialStockLot; it snapshots the receipt unit cost in the line and lot.
- Material issue/return/wastage services use atomic transactions and row locks for the balance, lot, issue and production line. Tests cover insufficient stock, multiple locations, returns to the original lot, and return/wastage not exceeding one issue.
- Physical stock count submission is non-mutating; approval applies a correction movement, rejects stale counts, and is covered by tests.
- Offcut action locks the offcut row and only permits transition from Available, preventing repeated use/discard through that endpoint.
- Production API restricts manager job visibility by customer department, staff visibility by assignment, and prevents normal Production completion without passing Final QC.

### Concrete workflow limitations / unresolved rules

1. **Goods receipt is all-pending, not quantity-based:** `receive()` loops through each PurchaseItem and receives its entire `pending_quantity`. The API payload does not accept per-line received quantities. Therefore the PurchaseOrder model's Partial status is not practically achieved by a partial quantity receipt in this endpoint; it only remains Partial if a line is left pending for another reason. Confirm whether SADACO needs partial deliveries. If yes, add explicit per-line quantities, validate each against pending quantity, and preserve atomic receipt posting.
2. **Offcut is not stock-integrated:** `offcut_create_api` creates a ReusableOffcut row but no stock movement or reduction from a source job's issued material. `offcut_action_api` marks an offcut Used/Discarded but creates no movement, usage record, or cost allocation. The row lock prevents duplicate status transition, but offcut quantities are not currently part of the stock ledger. Do not count offcut area as available stock or costing credit until the intended material accounting rule is defined and implemented.
3. **Offcut dimensions/area are caller-supplied independently:** the endpoint accepts length, width and usable_area_sqft as separate values; source does not calculate/validate area from dimensions. Validate unit conversion, usable-area ceiling and material/thickness match before treating area as reliable.
4. **Shared purchase-rate field is department-agnostic:** receipt posting overwrites the global `MaterialVariant.purchase_rate` with the latest received item cost, while department/location cost lots retain the actual receipt-specific rate. This can make the master rate represent whichever department last received stock. Decide whether it is an informational latest rate, weighted average, or department-specific rate; costing must use a clearly specified basis. Existing lot-based issue cost is the safer historical source.
5. **Legacy Product inventory remains separate:** receipt and issue paths for legacy Product items update `Product.stock_quantity`; MaterialVariant items update department/location balances. Reports must not aggregate these as if they were one ledger.
6. **Purchase receipt regression coverage is narrower than the workflow:** existing tests prove a full receipt creates one material movement/line/lot and that a second receipt after completion is rejected. They do not establish partial quantity delivery, multiple receipt batches for one line, rollback after a failure mid-loop, or concurrent receive attempts. Add tests after deciding the partial-delivery requirement.

### Next action

Before modifying code, settle the business rule for partial deliveries and offcut accounting. The source review has isolated those two product decisions; inventing them would risk changing stock and costing semantics. Once confirmed, implement only the selected behavior with API-level regression tests and transaction rollback/concurrency coverage.

This remains a source-level review only. No Django test command, migration, Neon write, production change, merge, or deployment was performed.


## 2026-11-16 — Partial Goods Receipt implementation (CI pending)

- Implemented per-line receipt quantities in `purchase/api.py`. New clients may submit `items: [{purchase_item_id, received_quantity}]`; omitted lines are not received, zero quantities are skipped, and at least one positive quantity is required.
- The API rejects duplicate/foreign purchase-item IDs, malformed or negative quantities, quantities above the remaining pending amount, and quantities with more than two decimal places. Material receipts still require a stock location.
- Existing clients that omit the `items` array retain the prior behavior of receiving all pending quantities. This keeps the endpoint backward compatible while the UI is migrated.
- Receipt posting remains inside the existing atomic transaction and PurchaseOrder row lock. Each partial batch creates its own GoodsReceipt, GoodsReceiptLine, stock movement and receipt-backed cost lot. PurchaseItem.received_quantity and PurchaseOrder status are updated from the accepted batch; the order remains Partial while any quantity is pending.
- Added regression tests for two receipt batches against one line (1.5 then 1.0 from an order of 4), stock/lot totals and Partial status, plus over-receipt rejection without stock writes.
- Updated the React Purchase Management page to open a quantity-entry receipt dialog showing ordered, already received and pending quantities, with supplier reference and location fields.
- Commits: API partial receipt support `ed2d6f129b224b1614e24ea0c5233716eb1b641a`; regression tests `c38786252a421d58d08bd5d8062fd44cd4a132bd`; UI `8589b8cc7dc3c3fceb03c82ae986d7574b795917`; quantity precision validation `51b4786723b6ba84aa5f46e41df3ec8b9b2d2de0`.
- GitHub Actions CI runs #207 and #208 were triggered by these commits; their final status must be checked before calling the implementation verified.
- No Neon database, production, `main`, or Render deployment was changed. No local Django or Playwright test command was run in this session.


## 2026-11-16 — Offcut workflow source review (read-only)

- `ReusableOffcut` currently stores material, department, location, thickness, length, width, usable area (sq ft), source job, target job and status. It does not retain the originating MaterialIssue, receipt lot, original material cost, or a consumed-area quantity.
- `offcut_create_api` creates only the ReusableOffcut row. It does not validate that usable area is less than or equal to the rectangle area, does not reconcile the supplied dimensions with the area, and does not create an `OFFCUT_IN` movement.
- `offcut_action_api` changes Available to Used/Discarded and records the target job for Used. It does not record how much area was consumed, decrement any offcut balance, link a material requirement, or create a costed issue.
- The stock ledger balance is denominated in `MaterialVariant.unit` (for example, Sheet), while the offcut model stores area in square feet. Adding `usable_area_sqft` directly to the existing sheet quantity would mix units and corrupt the balance. The existing `OFFCUT_IN` movement type alone does not solve that unit mismatch.
- Production UI currently exposes receipt-batch issue, return and wastage flows; no matching offcut registration/selection/consumption interface was found in the reviewed Production Management page.
- Safe next design: retain offcuts as individually traceable pieces with dimensions and square-foot area, and add a separate area-based ledger/consumption record tied to the source issue/receipt lot and target production material. Only calculate cost when source-lot cost and the material's source sheet area are known; do not infer sheet size or value from the current MaterialVariant record.
- No offcut code, schema, database, `main`, or deployment was changed during this review. Implementation is held pending confirmation of the business unit/cost rule.


## 2026-11-16 — Offcut area ledger implementation (CI pending)

- Added `ReusableOffcut.source_issue`, `source_lot` and a six-decimal `cost_per_sqft` snapshot. New offcuts must be registered against an issued, receipt-costed Sheet material issue; legacy offcut rows remain nullable and readable.
- Registration validates positive dimensions/usable area, checks usable area does not exceed the measured rectangle (mm² → sq ft), verifies material/department/source-job/receipt-lot consistency, and prevents aggregate registered offcut area from exceeding the unreturned/unwasted source issue's sheet area.
- Sheet area uses the material master dimensions already present on `MaterialVariant`; cost per sq ft is the exact source lot unit cost divided by that sheet area. The sheet-stock balance is deliberately not incremented or decremented by square feet.
- Added `OffcutUsage` as a separate area-based consumption ledger, linking each partial use to a target ProductionJob and matching ProductionMaterial line. Each usage snapshots cost per sq ft and rounded total cost. Multiple partial uses are supported; the offcut is marked Used only when its full usable area has been allocated.
- The offcut API now returns source receipt, cost snapshot, remaining area and usage history. Production detail exposes the material master ID; the Production UI can register a measured offcut from a source issue and allocate available area to a matching material line in the current job.
- Added regression coverage for source-lot cost snapshot, rectangle-area validation, partial use and cost allocation, full-use status transition, and material mismatch rejection.
- Cost attribution is recorded in `OffcutUsage`, but no existing consolidated production-job costing/report service was found in this audit. This change does not yet calculate source-job salvage credit or roll offcut usage into a final job margin/report; those require a separate, explicit costing/reporting step. No sheet stock quantity is altered by area-based offcuts.
- Files changed: `inventory/models.py`, `inventory/migrations/0006_offcut_area_cost_ledger.py`, `inventory/api.py`, `inventory/tests.py`, `production/api.py`, `frontend/src/pages/ProductionManagement.jsx`.
- CI runs #214–#219 were triggered; final results must be checked after completion. No local Django/Playwright command, Neon write, production change, `main` merge, or Render deployment was performed.


## 2026-11-16 — Offcut cost transfer and production-job material costing

- Added discard snapshots `discarded_area_sqft` and `discarded_cost`. Discarding an offcut now writes off only its remaining area at the original source-batch cost per sq ft; previously consumed area remains allocated to the jobs that used it.
- Added `_job_material_cost_summary(job)` to the Production Job detail response. The calculation reports receipt-backed issue cost, returned-material credit, generated-offcut salvage credit, discarded-offcut write-off, offcut cost consumed by this job, remaining reusable-offcut inventory value and net material cost.
- Cost transfer treatment: when a reusable offcut is registered, its full area value is credited against the source job and held as reusable inventory value; when used by another job, its consumed area cost is charged to that target job; if remaining area is discarded, the source job receives the write-off. This prevents counting the same area as both source-job consumption and target-job consumption.
- Legacy material issues without a recorded unit rate are excluded from monetary totals and surfaced as an unpriced issue count. No estimated price is substituted.
- Production Job detail UI now displays the material cost reconciliation and permits discarding remaining offcut area with the resulting write-off displayed in the offcut record.
- Added a regression test covering ₹100 issue cost, ₹31.25 salvage credit for 10 sq ft, ₹12.50 transfer for 4 sq ft to another job, and ₹18.75 write-off for the remaining 6 sq ft. Expected source-job net material cost after discard is ₹87.50; target-job offcut material cost is ₹12.50.
- This is a receipt-backed raw-material cost view, not a complete job margin: labour, machine time, overhead, consumables and sales revenue are not included. No finance transactions or accounting journal entries are created by this operational costing view.
- CI run for the final commit is pending. No local Django/Playwright command, Neon write, production change, `main` merge, or Render deployment was performed.


### Additional safeguard — offcut area cannot be returned or wasted twice

- A receipt-backed sheet issue now reduces its returnable/wastage quantity by the sheet-equivalent of all offcut area already registered against that issue. This prevents a sheet area already transferred into reusable offcut inventory from also being restored as a whole/partial sheet return or counted again as sheet wastage.
- Added regression tests for both return and wastage rejection when the requested sheet-equivalent quantity would overlap registered offcut area.
- The source-issue offcut-registration guard already checks cumulative registered offcut area against the issue's remaining area after prior returns and wastage.


### Purchase-to-production integration coverage and physical offcut dimensions

- The reusable-offcut workflow regression fixture now receives its source sheet through the real Purchase Goods Receipt API, then verifies the receipt lot and department stock balance before issuing it to the source production job. This joins the previously separate purchase-receipt and offcut-costing tests into one cross-app integration path.
- Offcut registration now validates that the measured piece dimensions fit within one physical source sheet, allowing rotation. The prior area-only check could accept an impossible long/narrow rectangle whose area was small enough but whose length exceeded the sheet.
- Added a regression test for an offcut dimension that exceeds the source sheet even though its declared usable area is small.
- CI for these newest commits is pending; no production DB, main, or deployment was changed.


### Read-only stock ledger and receipt-lot reconciliation

- Added `reconcile_material_stock_balance()` and the department-scoped read-only endpoint `/api/inventory/materials/reconciliation/`.
- The report compares recorded department/location balance with the reconstructed movement ledger and separately verifies each receipt lot (`original_quantity - issued_quantity + returned_quantity`).
- Wastage movements are intentionally treated as annotations with zero additional stock delta because the sheet quantity was already deducted at original issue. Offcut area remains outside the sheet-unit stock balance.
- Opening/legacy quantities not backed by receipt lots are reported as `unbatched_quantity` warnings rather than falsely labelled as movement mismatches. Such quantities remain uncosted/unbatched and are not eligible for the receipt-lot issue workflow until a legitimate costed batch exists.
- Added tests for a balanced issue+wastage path and for separately identifying unbatched opening stock. This report is diagnostic only; it performs no stock correction or write.
- CI for the reconciliation endpoint and new tests is pending. No database, production, main, or deployment changes were made.

- Added a Stock Reconciliation tab to Material Master & Job Costing. Authorized users can refresh a read-only view of recorded stock, movement-derived expected stock, receipt-lot remaining stock, differences and unbatched quantities. The API is department-scoped; no automatic corrections are offered.
- Added an endpoint regression test confirming a department manager cannot see another department's balance through the reconciliation report.


## 2026-11-16 verified opening-stock costing workflow

- Opening movements without verified cost remain unbatched and are not eligible for production issue. No current Material Master rate is copied into historical stock, and no zero/default cost is silently assigned.
- MaterialStockLot now supports two mutually exclusive sources: a Goods Receipt Line or an Opening Stock Movement. The database enforces exactly one source.
- Founder/Admin can review uncosted opening movements and register a costed opening batch only by entering an explicit non-negative unit cost and a mandatory source reference (invoice, approved valuation sheet or other verified record).
- Registration locks the opening movement and department/location balance, prevents duplicate costing, and refuses the operation when the opening quantity exceeds the currently available unbatched balance.
- The resulting batch uses the existing issue/cost attribution workflow; issue cost is snapshotted from that lot. Receipt-lot reporting and offcut source labels now support both purchase-receipt and opening-stock origins.
- Department managers cannot assign historical opening-stock costs. This is Founder/Admin-only because it changes historical inventory valuation.
- No historic rows are automatically costed, no stock quantities are changed by the costing registration itself, and no production/finance database was written.
- Regression coverage added for verified reference enforcement, manager authorization, and issuing against a verified opening batch. CI validation is pending.

## 2026-11-16 — Production Material Master linkage and issued-quantity guard

- Production material requirements can now select a shared Material Master item. The form copies the material name and stock unit from the selected MaterialVariant rather than trusting user-entered labels.
- A production requirement cannot link both a finished Product and a MaterialVariant.
- Removed `issued_quantity` from the ProductionMaterial form. A caller-supplied `issued_quantity` is ignored; issued quantity can only be incremented by the inventory issue service, which creates the stock movement, decrements the selected cost lot and records the receipt/opening-batch unit cost.
- Production options now expose active Material Master choices; the React Production Management form lets a manager select one when creating a material requirement.
- Regression tests cover Material Master linkage, authoritative master name/unit, ignoring a forged issued quantity, and rejecting simultaneous Product and MaterialVariant references.
- This closes a path that could previously mark material as issued without stock movement or issue-cost attribution.
- CI run #276 completed successfully for commit `947131b8b098869fce533f0020512ab6def4f7e3`: Django system checks, committed migrations, migration-plan verification, Django regression tests and frontend build all passed. This is GitHub CI on its PostgreSQL service database, not Neon clone or Production DB validation.
- No Neon, Production DB, `main`, merge, or deployment was changed.


## 2026-11-16 stock reconciliation correction handling

- The read-only stock reconciliation previously treated an approved physical-count correction as an unknown movement. That could report a false ledger mismatch even though the approved count had correctly updated the stock balance.
- Reconciliation now processes movements chronologically and treats CORRECTION / CLOSING rows as post-movement balance snapshots, resetting the running expected balance to balance_after. Wastage remains an annotation and does not decrement stock a second time.
- Regression coverage now verifies that an approved negative physical-count adjustment reconciles to the approved balance, while still reporting the quantity as unbatched when no cost lot exists.
- No stock rows were changed by this code fix; it only corrects the read-only reconciliation calculation.


## 2026-11-16 production machine and direct-labour costing

- Added an append-only ProductionCostEntry ledger with immutable unit-rate and total-cost snapshots. Machine / operation entries reference an active approved MachineRate; direct-labour entries reference an active staff member with a verified monthly StaffCompensation record.
- The machine rate selector uses only existing seeded rates: Laser Cutting ₹20/minute, Laser Engraving ₹25/minute, and CNC Multy Wood 5mm/6mm/8mm at ₹50/₹50/₹60 per sq ft. Material-specific CNC entries must match the selected job Material Master line and thickness. No new rates are seeded.
- Direct labour is calculated only for monthly-paid staff using the configured 26 working days and 8.25 productive hours/day (or that staff record's explicitly configured values). Work-based staff are excluded because no per-work rates are supplied. Staff without an active monthly compensation record cannot be costed.
- Cost entries are manager-only, department-scoped through the job and staff checks, and have no edit/delete endpoint. The unit rate and amount are snapshotted so later rate or salary changes do not rewrite historic job costs.
- Manager job cost summary now reports material cost, machine / operation cost, direct labour cost, total conversion cost, and total tracked job cost. This is not a complete margin calculation: revenue, overhead, consumables and any unprovided rates remain outside the total.
- The production issue history now displays verified opening-stock lot references and their evidence reference; it no longer assumes every cost lot has a purchase receipt.
- Regression suites for production costing and reusable offcut ledger were added to CI. CI remains the acceptance gate; no local tests, Neon validation, production writes, merge or deployment are claimed.

## 2026-11-16 duplicate offcut endpoint correction

- Removed obsolete duplicate definitions of the offcut create/action APIs that were shadowing the newer receipt-traceable, dimension-validated and cost-aware implementations. This restores the intended source-issue link, sheet-dimension checks, partial area usage, job material matching, cost snapshots and return/wastage safeguards.
- Changed row locking to lock only the primary production material / issue rows when nullable related objects are selected, avoiding PostgreSQL's unsupported FOR UPDATE on the nullable side of an outer join.
- Added the previously unexecuted reusable-offcut regression suite to the CI workflow so these paths are exercised on subsequent runs.


## 2026-11-22 — Global stock reconciliation summary implementation

- Updated `/api/inventory/materials/reconciliation/` so reconciled, mismatch and unbatched counts are computed across the complete permission-scoped set of stock balances, not just the current 100-row page.
- The calculation processes balances in bounded 100-row chunks and prefetches their movement and receipt-lot issue histories per chunk, avoiding a single unbounded in-memory load.
- The response now declares `summary_scope: all_visible_balances`; row details remain paginated and manager department scoping remains applied to both page data and global summary.
- Added a regression test with 205 balances and one deliberately inconsistent balance on page one. It asserts page one and page two return identical global totals (204 reconciled, 1 mismatch, 1 unbatched) while page two rows themselves are all reconciled.
- This is a source change only. GitHub Actions must validate it; no local Django tests, Neon/production database writes, Main merge or deployment are claimed.


## 2026-11-22 — Opening-stock costing pagination

- Removed the fixed 500-row opening-stock review cap. The uncosted opening-stock API now returns 100 rows per page with total count and navigation metadata.
- Updated Material Master & Job Costing → Opening Stock Costing to navigate all pages and show the total number of uncosted opening movements.
- Updated Stock Reconciliation labels and explanatory text to make clear that the summary covers all visible balances, not the current page.
- Added API regression coverage for 205 uncosted opening movements across three pages, including complete, duplicate-free ID coverage.
- Source changes only; CI and database validation remain pending.


## 2026-11-22 — Stock balance and movement API pagination

- Replaced the unbounded Material Stock API response with stable 100-row pagination. Search and department filters are applied before counting, slicing and aggregating total quantity.
- Replaced the 500-row material movement cap with stable 100-row pagination, ordered newest-first with primary-key tie-break.
- Both endpoints now return count, total_count, page, page_size, total_pages and navigation flags; stock total quantity remains the aggregate across the full filtered queryset, not just the page.
- Added regression tests covering 205 stock balances and 105 movements, proving complete duplicate-free coverage across pages and preserving whole-filter total quantity.
- UI callers must be checked/migrated to consume pagination before this API change is considered end-to-end complete. CI validation pending; no local tests or database writes performed.
