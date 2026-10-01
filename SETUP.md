# SADACO React + Vite Setup

1. Create and activate the Python virtual environment.
2. Install `requirements.txt`.
3. Configure `.env` from `.env.example`.
4. Run Django migrations.
5. Start Django on port 8000.
6. Enter `frontend/` and run `npm install`.
7. Start Vite with `npm run dev`.

The frontend communicates only through `/api/...` JSON endpoints. Django HTML templates are not used.
