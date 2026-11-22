# SADACO ERP — Phase 1 Delivery Plan

**Status:** Planning baseline; implementation starts after architecture and migration review.  
**Scope source:** SADACO ERP Final Requirements & Functional Specification, sections 1–9 and 21–24.

## Phase 1 scope

1. Authentication, staff identity, roles, departments, division membership and permissions.
2. Founder dashboard shell with date filters and data contracts for KPIs.
3. CRM: customer master, enquiries, source/status, assignment, follow-up and communication history.
4. Quotations: configurable inputs, approval states, discount approval and PDF output.
5. Orders: unique order IDs, lifecycle, advance/balance, delivery date and assigned staff.
6. Design management: file metadata, revisions, comments and customer approval; only approved revisions may enter production.
7. Job cards and production stages, including owner, planned/actual dates, time, evidence and status.
8. Staff task assignment, deadlines, issue/delay reporting and manager alerts.

## Phase 1 acceptance criteria

### Identity and access
- Founder can view and administer all divisions and audit history.
- Manager access is limited by configured permissions and approval limits.
- Designers, production support, CNC and polishing staff can access only their assigned work and permitted fields.
- API tests prove cross-division and unauthorized record access is denied.

### CRM
- Customer records include the fields and enquiry sources/statuses in the PDF.
- Duplicate checks use mobile number and matching details without silently merging records.
- Follow-up reminders and overdue indicators are visible.
- Communication history is linked to the customer/enquiry.

### Quotations
- Quotation supports customer, product/service, dimensions, quantity, material, labour, machine, finishing, packing, delivery/installation, discount and configurable tax.
- Statuses: Draft, Pending Approval, Sent, Accepted, Rejected, Expired.
- Founder-configured discount limits govern Manager approvals; special discounts require approval.
- PDF includes company/customer details, product/images, dimensions, itemized price, terms and validity.
- Unspecified tax/rates/approval limits are not defaulted to invented values.

### Orders
- Every order has a unique ID and stores division, customer, items, amount, advance, balance, delivery date, installation requirement and assigned staff.
- Lifecycle transitions are validated; delayed tasks and delivery deadlines are flagged.
- Production cannot proceed until design approval and normal advance requirements are satisfied, unless an authorized exception is recorded.

### Design and production
- Supported file metadata includes CorelDRAW, AI, SVG, PDF, DXF and common image/reference formats.
- Design revisions and approval comments are retained; approved versions are locked and changes create a new revision.
- Job cards link to order and approved design.
- Production stages record employee, start, expected/actual completion, status, remarks, material needs/usage, labour time and evidence.
- Every production task has an assigned owner.

## Required test suites

- Unit tests for state transitions, order numbering, approval thresholds and validation.
- API tests for CRUD permissions, division isolation and audit records.
- Integration tests for enquiry → quotation → order → design approval → job card.
- Frontend tests for critical forms, validation, navigation and role-specific visibility.
- Playwright end-to-end tests for Founder, Manager, Designer and Production Staff workflows.
- Regression test: no production access with unapproved design; no silent edit/delete of audit-sensitive records.

## Exclusions from Phase 1

Inventory ledger, purchase workflow, full accounts, salary, attendance, QC, delivery execution, installation, feedback, notifications beyond Phase 1 workflow alerts, WhatsApp integration, advanced costing and multi-location are later phases unless a Phase 1 dependency requires only a minimal interface contract.

## Phase gate

Phase 1 is complete only when all acceptance criteria and automated tests pass, a review build is available, and SADACO approves the working phase. Do not start Phase 2 before approval.
