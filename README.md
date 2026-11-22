# SADACO ERP — Clean Rebuild

This repository is being rebuilt from the approved SADACO ERP requirements PDF.

- Repository retained; historical Git objects and commits remain available.
- Legacy application files removed from the default branch.
- New implementation must be designed against the PDF requirements and acceptance criteria.
- Existing Neon production database schema and Django migration history are retained; operational records have been cleared.
- Do not deploy or run migrations until the new architecture, migration plan, and environment configuration are reviewed.

## Rebuild principles

1. One shared database with strict division-level access for SADACO Creatives, SADACO CNC, and SADACO Decor Co.
2. Role-based access and auditable approval workflows.
3. No invented prices, rates, or business rules.
4. Stock, costing, finance, order lifecycle, HR, QC, delivery, and reporting must satisfy the PDF.
5. Automated backend, frontend, integration, and end-to-end acceptance tests are mandatory before production deployment.
