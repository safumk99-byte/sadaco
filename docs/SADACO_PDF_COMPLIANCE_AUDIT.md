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

- The final requirements PDF is the sole source of truth.
- Legacy operational/catalogue data may be fully removed and rebuilt; do not preserve old demo products, old rates, orders, stock, customer records or old workflow history merely because they exist.
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
