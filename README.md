# SADACO — React + Vite Frontend / Django API Backend

SADACO is now an API-first application with a fully React + Vite frontend.

## Architecture

- Frontend: React 19 + Vite + React Router + Tailwind CSS
- Backend: Django 5.2 REST-style JSON APIs
- Database: PostgreSQL / Neon
- Authentication: Django session authentication exposed through JSON APIs
- Web Push: Django service-worker endpoint + React subscription UI

## Important

There are no Django HTML templates or template-driven application routes in this version. The management UI and customer portal are React pages. Django is retained for authentication, business logic, database models, migrations, API endpoints, PDF/report generation support, and Web Push.

## Run

### Backend

```bash
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite development server proxies `/api` requests to Django. See `frontend/vite.config.js`.

## Customer Portal

Customer registration and the complete customer portal are React routes:

- `/register`
- `/login`
- `/customer`

Customer portal features include products, requests, quotations, design responses, orders, notifications, feedback, and profile management.

## Playwright E2E testing

1. Copy/fill `.env.test` with the SADACO test username and password.
2. Run `npm install` in the project root.
3. Run `npx playwright install chromium`.
4. Start Django and the React/Vite frontend.
5. Run `npm run test:e2e:full`.
6. View the report with `npm run test:e2e:report`.

The `.env.test` file is ignored by Git so test credentials are not committed.

### React + Vite CSRF

`settings.py` includes `CSRF_TRUSTED_ORIGINS` for `http://localhost:5173` and `http://127.0.0.1:5173`, which prevents Django's Origin checking from rejecting local React login requests.
