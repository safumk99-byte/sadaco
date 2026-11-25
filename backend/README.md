# SADACO ERP Backend

Django + Django REST Framework backend foundation for the PDF-driven rebuild.

## Local setup

```powershell
py -3.12 -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python manage.py check
python manage.py makemigrations core
python manage.py migrate
python manage.py runserver
```

SQLite is the local default. Set `DATABASE_URL` to a PostgreSQL connection string for PostgreSQL development/testing. Production secrets must be environment variables and must never be committed.

## Important

- This scaffold is not yet connected to Neon Auth.
- No production migrations have been generated or applied.
- Division/role authorization, business services, API serializers, and full tests are the next implementation tasks.
- Never point local migration/testing commands at production.
