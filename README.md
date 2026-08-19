# SADACO Management System

## Stack
- Django
- PostgreSQL
- Django Templates
- Tailwind CSS

## Phase 1
1. System Foundation — completed
2. Authentication / Users / Roles / Permissions — in progress
3. Staff Management
4. Product Management

## System Foundation completed
- Django project configuration
- PostgreSQL environment configuration
- Static/media configuration
- Common base template
- Global system information context
- Database health-check endpoint: `/health/`
- Common 404/500 templates
- Tailwind CLI configuration
- Environment variable template
- Foundation test

## Development rule
Complete each module fully — database/schema, backend, routes, templates/UI,
permissions/security, validation, testing, and necessary reports — before moving
to the next module.

## Current completed modules
- System Foundation
- Authentication / Users / Roles / Permissions
- Staff Management
- Product Management
- Inventory / Stock Management
- Management Dashboard


## Authentication foundation completed in this version

- Django authentication login/logout
- UserProfile model
- Role choices: Super Admin, Institution Admin, Manager, Staff
- Role-aware user creation
- Role-aware user listing
- Role protection decorator
- Admin registration for UserProfile
- Authentication templates
- Authentication migration


## Authentication complete
- User create/list/edit
- Activate/deactivate accounts
- Admin password change
- Current-user profile
- Role-to-Django-group synchronization
- Role-protected management routes
- Authentication tests


## Local database behavior

The project now uses SQLite automatically when `POSTGRES_HOST` is not set.
This makes the starter project run immediately on Android/Termux and on a
fresh local computer.

PostgreSQL is still supported: set `POSTGRES_HOST`, `POSTGRES_DB`,
`POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_PORT` in the environment
when the real PostgreSQL database is ready.


## Database configuration

SADACO is PostgreSQL-only. Local SQLite fallback has been removed.
The project loads `.env` with `python-dotenv` and connects to Neon using SSL.
See `SETUP.md` for the exact setup sequence.


## UI pass
All currently implemented pages have a responsive SADACO UI: login, dashboard, users, user forms, password management, profile, staff, products, and error pages.


## Completed Modules
- System Foundation
- Authentication / Users / Roles
- Staff Management
- Product Management
- Inventory / Stock Management
- Customer & Sales Management: Customers, Enquiries, Quotations and Order Confirmation

## Pending Known Issue
- Existing staff records created before the photo-upload fix may not have a stored photo. Re-uploading a photo through Staff Edit should store and display it using the corrected `/media/` configuration.
