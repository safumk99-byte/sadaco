# SADACO ERP — Foundation Architecture (Proposal)

**Status:** Architecture baseline for review; no production migrations or deployment authorized by this document.  
**Source of truth:** `SADACO_ERP_Final_Requirements_v2.pdf` (11 pages, version 1.0).  
**Currency:** INR (₹).

## 1. Business boundaries

One ERP serves three divisions:
- SADACO Creatives
- SADACO CNC
- SADACO Decor Co.

Use one shared customer and identity system. Every division-owned transaction must carry a division reference. Founder/Super Admin has consolidated visibility and drill-down; other roles are restricted by role, department, assignment and configured approval limits.

## 2. Proposed application architecture

- **Backend:** Django + Django REST Framework; domain logic and authorization remain server-side.
- **Frontend:** React + Vite; responsive web application, with mobile-friendly layouts.
- **Database:** Existing Neon PostgreSQL production database; do not create another database without an explicit decision.
- **Authentication:** Use the existing managed Neon Auth capability only after its integration contract is verified; do not assume its tables are application models. Map authenticated identities to ERP staff and role assignments.
- **Files:** Store design files, images, job evidence and documents through a private object-storage abstraction. Provider and retention configuration remain deployment decisions.
- **API:** Versioned REST API; frontend must not bypass business rules or access PostgreSQL directly.
- **Environments:** local/test/staging/production separation; production migrations only after reviewed migration plan and tested release.

This is a proposed implementation stack, not a claim that the PDF mandates these technologies.

## 3. Domain modules and dependencies

1. Identity, staff, departments, divisions, roles and permissions.
2. CRM and enquiry follow-up.
3. Product/service catalogue and configurable quotation/rate settings.
4. Quotations, approval workflow and PDF output.
5. Orders and lifecycle state machine.
6. Design files, revisions and customer approval.
7. Job cards, production stages, staff assignments and work-time records.
8. Inventory/material master, stock ledger, offcuts and wastage.
9. Suppliers, purchase requests, purchase orders, receipts and payables.
10. Job costing (estimated and actual), pricing and profitability.
11. Accounts, receipts, expenses, cash/bank/UPI, receivables and payables.
12. CNC/laser operations, QC, delivery and installation.
13. Attendance, leave, salaries and work-based payments.
14. Feedback, complaints, notifications, KPIs and reports.

Dependencies: identity/divisions precede all transactional modules; CRM precedes quotations and orders; approved designs precede production; purchase receipts and material issues feed stock and actual job cost; QC pass gates delivery; finance postings are linked to source documents and audit history.

## 4. Core data model principles

- Use stable primary keys, created/updated timestamps, actor references and explicit status fields.
- Division-owned business records reference a division; shared customers may be used across divisions.
- Separate master data from transactional ledgers and immutable historical snapshots.
- Preserve historical purchase rates on stock receipts/issues and job-cost lines; later rate changes must not rewrite completed jobs.
- Stock balance is derived from a movement ledger: opening, receipt, issue, return, reusable offcut, wastage and adjustment/closing.
- Financial and stock corrections use authorized reversal/correction entries, never silent deletion.
- Approval records capture requester, approver, decision, timestamp, reason and the affected record/version.
- Use decimal monetary/quantity fields with explicit units; never use binary floating point for money.
- Do not create default rates, suppliers, reorder levels, tax values, overhead percentages, discounts or unprovided work-based payment rates.

## 5. Required business invariants

- Normal production advance is 50%, unless an authorized exception is approved.
- Production cannot start without an approved design.
- Each order has a unique human-readable order ID (format example in PDF: `SAD-2026-0001`).
- Each production task has an assigned owner.
- Material issue and return are recorded against the relevant job/order and employee.
- QC must pass before delivery.
- Final payment is required before delivery unless approved credit exists.
- Manager discount, purchase and expense limits are configured by Founder; unspecified limits remain unset until configured.
- Salary is recorded once as business expense; labour allocation to jobs is cost attribution and must not duplicate salary expense.
- Estimated and actual costs remain separate; actual consumption and reusable offcuts are recorded.
- Margin and markup are distinct calculations.

## 6. Costing rules from the specification

- Sheet area = width (ft) × height (ft).
- Purchase rate/sq ft = full-sheet purchase rate ÷ sheet area.
- Estimated material cost = estimated consumed area × purchase rate/sq ft.
- Laser cutting = actual cutting minutes × configured cutting rate; PDF initial rate ₹20/min.
- Laser engraving = actual engraving minutes × configured engraving rate; PDF initial rate ₹25/min.
- CNC cost = job area × configured material/thickness rate. Supplied Multy Wood rates: 5 mm ₹50/sq ft; 6 mm ₹50/sq ft; 8 mm ₹60/sq ft.
- Total production cost = material + machine + labour + consumables + wastage + packing + delivery/installation + allocated overhead.
- Profit = selling price − total production cost.
- Margin (%) = profit ÷ selling price × 100.
- Markup (%) = profit ÷ total cost × 100.
- Monthly salary allocation basis in PDF: 26 × 8.25 = 214.5 productive hours. Salary allocation is not a second salary expense.
- Wastage is actual, not a universal fixed percentage. Reusable offcuts return to stock.

## 7. Data supplied vs. configuration still required

Seed only values explicitly present in the PDF. Supplied acrylic, Indian sheet, mirror, laser, CNC and monthly salary rates belong in versioned rate records with effective dates. Missing retail rates remain blank/unavailable, not zero. Shibili and Sakeer work-based rates remain unset. Additional CNC rates, consumables, packing, delivery, installation, suppliers, reorder levels, tax, overhead allocation and approval thresholds are configured by authorized users.

## 8. Security and audit

- Deny by default; enforce role, division, department and assignment permissions on every API operation.
- Founder/Super Admin has full cross-division control.
- Manager permissions are limited by Founder-configured approval limits.
- Staff see assigned work and explicitly permitted material/time updates only.
- Protect salary, customer and financial information.
- Audit rate, discount, approval, workflow, stock and finance changes.
- Do not expose private design/evidence files through public URLs.
- Add automated tests for permission boundaries and cross-division data isolation.

## 9. Delivery sequence

- Phase 1 — Core: login/roles, Founder dashboard, CRM, quotations, orders, design, tasks and production.
- Phase 2 — Factory & Finance: inventory, purchasing, CNC, QC, accounts, delivery and installation.
- Phase 3 — Complete: HR/salary, KPIs, feedback, notifications, advanced reports and WhatsApp.
- Phase 4 — Future: advanced ERP, automated costing, machine analytics, finance analysis, sales partners and multi-location.

Each phase must be implemented, tested, reviewed and approved before the next phase begins.

## 10. Immediate next engineering gate

Before creating application migrations:
1. Confirm the final backend/frontend stack and repository layout.
2. Produce an entity-relationship model and field-level data dictionary.
3. Map Neon Auth integration and environment variables without exposing secrets.
4. Produce migration ordering, constraints, indexes and rollback strategy.
5. Write Phase 1 acceptance tests from the PDF.
6. Review and approve the architecture/migration plan.

**Current infrastructure note:** The Neon production branch exists and its `public` schema is currently empty; managed `neon_auth` tables remain. No application tables or migrations are present on the default branch at this checkpoint.
