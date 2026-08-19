# SADACO Setup

## 1. Create the environment file

Copy `.env.example` to `.env`.

Fill in only your real Neon PostgreSQL password:

`POSTGRES_PASSWORD=YOUR_NEON_PASSWORD`

Do not commit `.env`.

## 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

## 3. Check the project

```bash
python manage.py check
```

## 4. Apply database migrations

```bash
python manage.py migrate
```

## 5. Create the first admin account

```bash
python manage.py createsuperuser
```

## 6. Start the server

```bash
python manage.py runserver
```

Open:

`http://127.0.0.1:8000/`

## Database

SADACO uses PostgreSQL only. The default configuration targets the Neon
database supplied for this project and requires SSL.

No SQLite fallback is used.
