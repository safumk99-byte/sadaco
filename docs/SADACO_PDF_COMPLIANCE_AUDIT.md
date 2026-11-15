# SADACO ERP — PDF Compliance Audit & Implementation Tracker

**Authority:** `SADACO_ERP_Final_Requirements_v2.pdf` (11 pages; final source of truth)  
**Working branch:** `feature/phase-2-department-access`  
**Production policy:** Do not modify `main` or the production Neon branch during implementation.

## Acceptance rules

- The PDF is the business specification; existing code and demo data do not override it.
- Preserve genuine users, staff, departments and verified operational records.
- Remove/replace only confirmed demo products, prices and orders. Protect referenced records.
- Never invent unspecified prices, tax rates, approval limits, reorder levels, wastage percentages or overhead percentages.
- Financial, stock, rate, discount, approval and workflow changes must be auditable. Key stock/finance entries require correction/reversal, not silent deletion.
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
- CI status is not yet available for the latest commits; no test pass is claimed.
- Neon staging migration has not been run. Production database and `main` remain untouched.
