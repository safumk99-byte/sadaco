# SADACO ERP — Phase 1 Data Dictionary & Constraint Register

This document accompanies `docs/architecture/PHASE_1_DATA_MODEL.md`. It clarifies field semantics and implementation constraints; it is not an SQL migration.

## Common conventions

| Convention | Rule |
|---|---|
| PK | UUID primary key |
| FK | UUID foreign key with explicit delete behavior |
| Money | INR `NUMERIC(14,2)`; never float |
| Quantity | `NUMERIC(14,3)` unless a more precise unit is justified |
| Time | `TIMESTAMPTZ` for events; `DATE` for business dates |
| JSONB | Only for variable structured payloads such as dimensions; avoid hiding relational facts |
| Audit | Actor, timestamp, action, before/after and reason for sensitive changes |
| Tenant scope | `division_id` for division-owned records; enforce on every query/mutation |

## Phase 1 tables

| Table | Purpose | Required constraints and notes |
|---|---|---|
| divisions | Three business divisions | Unique code and name; seed the three PDF divisions |
| departments | Founder-configurable departments | Unique name within division; active flag |
| staff | People and employee profile | Unique external auth subject only after authentication is integrated |
| roles | Founder, Manager and staff role definitions | Unique immutable code |
| permissions | Fine-grained API/UI capabilities | Unique permission code; deny by default |
| role_permissions | Role-to-permission map | Composite primary key |
| staff_roles | Scoped role grants | Effective dates, grantor, division/department scope |
| staff_departments | Staff membership | Composite unique staff/department |
| audit_events | Append-only change history | No routine update/delete; index entity and time |
| approval_requests | Approval workflow | Requester, decision maker, timestamps and reason; no fabricated limits |
| customers | Shared customer master | Customer code unique; mobile indexed, not necessarily unique |
| enquiries | CRM enquiry | Division, source/status, owner, follow-up date |
| follow_ups | Reminder and action items | Due timestamp and completion trace |
| customer_communications | Contact history | Channel, direction, time, summary; no API integration assumption |
| quotations | Commercial offer header | Unique number, configurable tax, approval state, terms/validity |
| quotation_items | Quotation lines | Unique line number per quotation; quantity/unit/pricing snapshots |
| sales_orders | Confirmed order | Unique number; amount/advance/balance reconciliation |
| order_items | Order line items | Unique line number per order; quantity/unit/dimensions/price |
| order_assignments | Staff-to-order assignment | Assignment type, assigner and effective period |
| order_status_events | Immutable order lifecycle | From/to state, actor, timestamp and reason |
| design_records | Design work container | Belongs to order; assignee and status |
| design_revisions | Versioned artwork | Unique revision number; approved revision becomes locked |
| stored_files | Private file metadata | Unique storage key, checksum, uploader; bytes live outside DB |
| design_revision_files | Revision attachments | Composite primary key |
| design_approvals | Internal/customer approval evidence | Reviewer, decision, timestamp, comments |
| job_cards | Production job header | Links order and approved design revision |
| production_stages | Ordered manufacturing stages | Stage sequence unique per job; assigned owner |
| production_updates | Timestamped production reports | Actor, status, note/evidence |
| staff_tasks | Employee work assignment | One required assignee, deadline, priority and status |
| task_updates | Employee progress/issue reports | Reporter, update type, evidence and timestamp |

## Field-level validation register

### Identity
- Staff name must be non-empty.
- Staff access is inactive/revoked when role validity expires or staff is deactivated.
- Role assignment must be scoped to division/department where needed.
- Founder/Super Admin cross-division privileges are explicit, never inferred from a display name.

### CRM
- Customer name required; mobile optional as PDF does not require it to be mandatory.
- Normalize phone numbers for matching; retain entered display form.
- Enquiry source allowlist: WhatsApp, Instagram, Facebook, Phone, Direct Visit, Referral, Other.
- Enquiry statuses: New, Contacted, Quotation Sent, Follow-up, Confirmed, Lost.
- Due follow-ups must be queryable without loading all CRM records.
- Do not silently merge matching customers.

### Quotations
- Validity date must not precede issue date.
- Quantity must be greater than zero.
- Line total and header totals must reconcile using decimal arithmetic and an explicitly selected rounding policy.
- Tax rate may be null until configured; a null rate is not equivalent to zero tax.
- Approval required where Founder-configured discount rules demand it; missing thresholds block automated approval rather than defaulting permissively.
- Preserve the rate/description/quantity/price snapshots used at quotation issuance.

### Orders
- Unique order identifier generated atomically; do not rely on a client-generated number.
- Delivery date cannot be earlier than order date unless an authorized correction exists.
- Amounts must be nonnegative; advance cannot exceed the payable order value without a documented credit/refund adjustment.
- Balance reconciliation is checked in a transaction whenever a receipt, refund or authorized adjustment is posted.
- Normal 50% advance rule is enforced at production-start gate, with auditable exception approval.
- Order status transitions follow the PDF sequence; no direct status jumps without authorized workflow decision.

### Design
- Revision number starts at 1 and increments within one design record.
- Approved revision is immutable; edits create a new revision.
- Production job must reference an approved revision for that order.
- Uploaded content is private; validate actual file bytes/MIME server-side, not only extension.

### Production and task management
- Each production stage/task has one current accountable owner.
- Actual completion cannot precede actual start.
- No overlapping time entries for the same employee where time costing is later enabled.
- Evidence attachments retain uploader, timestamp and storage checksum.
- Rework is a recorded state, not deletion of a failed stage.

## Cross-entity invariants to enforce in domain services

1. Order, quotation, enquiry, design and job card division/customer relationships must be consistent.
2. A quotation converted to an order retains its source reference and pricing snapshot.
3. An order cannot be moved into production unless design approval and advance/approved exception conditions are satisfied.
4. Every order and production status transition writes both its specific event row and a general audit event in one transaction.
5. Staff access is checked against division, department, assignment and role at every endpoint.
6. A customer can exist globally, but enquiry/order access remains division-scoped.
7. Files attached to approved designs or completed jobs cannot be hard-deleted through normal application workflows.
8. Approval requests cannot be decided by the same actor when policy requires separation; exact separation-of-duty rules remain configurable until defined.
9. An order cannot be delivered unless QC has passed and final-payment or approved-credit conditions are met (Phase 2 delivery gate).
10. No balance, total, price or status supplied by the browser is trusted without server-side recomputation.

## Query/index implementation notes

Use B-tree indexes on foreign keys and common filter/sort fields. Use partial indexes for open tasks/follow-ups only after status semantics are fixed. Use normalized mobile as a generated/maintained search key, not as a unique customer identity. Avoid GIN indexes on all JSONB fields; index only demonstrated query predicates after query-plan review.

## Migration/rollback requirements

- Create one migration per coherent dependency group.
- Verify migration against a disposable Neon branch or local test database before production.
- Include data and schema preconditions/postconditions.
- Use explicit lock timeout and statement timeout in production rollout plan.
- Snapshot/backup production and validate restore procedure before applying any destructive or irreversible operation.
- Rollback application version and database migration strategy must be documented together.
