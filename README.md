# SADACO ERP — Clean Rebuild

This repository is being rebuilt from the approved SADACO ERP requirements PDF.

## Infrastructure and current checkpoint

- GitHub repository retained; legacy branches and historical Git objects have not been deleted.
- The default `main` branch contains the clean-rebuild documentation and will hold the new implementation.
- Neon project `sadco` and its production/default branch are retained.
- The Neon production `public` application schema is empty at this checkpoint; managed `neon_auth` tables remain.
- Render resources are intentionally untouched. Existing services and databases must be preserved; `sadaco` remains the target web service.
- No application migrations have been applied and no production deployment has been started.

## Source of truth

`SADACO_ERP_Final_Requirements_v2.pdf` is the sole business requirements baseline. Do not invent missing rates, tax values, approval limits, suppliers, reorder levels, wastage percentages or overhead allocations.

## Rebuild principles

1. One shared database with strict division-level access for SADACO Creatives, SADACO CNC and SADACO Decor Co.
2. Role-based permissions and auditable approval workflows.
3. Preserve historical rates and financial/stock audit trails.
4. Stock is tracked through movements; corrections use authorized reversal/correction entries.
5. Estimated and actual job costs remain distinct; labour allocation must not double-count salary expense.
6. Build in phases and obtain review/approval of each working phase.
7. Automated backend, frontend, integration and Playwright acceptance tests are required before production deployment.

## Planning documents

- `docs/architecture/FOUNDATION_ARCHITECTURE.md`
- `docs/implementation/PHASE_1_PLAN.md`
