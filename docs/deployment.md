# Deployment Guide

## Option A — Docker Compose (recommended for a self-contained demo/production box)

```bash
cp backend/.env.example backend/.env   # edit JWT_SECRET_KEY at minimum
export JWT_SECRET_KEY=$(openssl rand -hex 32)
docker compose up --build -d
```

Services started:

| Service | Port | Notes |
|---|---|---|
| `postgres` | 5432 | Persistent volume `postgres_data` |
| `minio` | 9000 (API), 9001 (console) | Persistent volume `minio_data` |
| `backend` | 8000 | FastAPI, connects to `postgres` + `minio` by service name |
| `frontend` | 4173 | Static build served via `serve` |

The backend's `docker-compose.yml` environment overrides `DATABASE_URL` to point at the
`postgres` service and `MINIO_ENDPOINT` at the `minio` service — no `.env` file is needed
inside the container for those two.

**Before going to production:**
1. Set a strong `JWT_SECRET_KEY` (never use the default).
2. Change the MinIO root credentials (`MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` in
   `docker-compose.yml`) and the corresponding backend env vars.
3. Put the backend behind a reverse proxy (nginx/Caddy) with TLS.
4. Set `CORS_ORIGINS` to your real frontend domain only.
5. Run Alembic migrations against Postgres: `alembic upgrade head` (see below).

## Option B — Bare-metal / VM (systemd + nginx)

1. Install Python 3.11, Node 20, PostgreSQL, and MinIO on the host.
2. Backend:
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env   # point DATABASE_URL at your Postgres instance
   alembic upgrade head
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```
   Wrap this in a `systemd` unit (`ExecStart=.venv/bin/uvicorn ...`) for auto-restart.
3. Frontend:
   ```bash
   cd frontend
   npm install
   npm run build
   ```
   Serve the `dist/` folder as static files via nginx, with `try_files $uri /index.html;`
   for client-side routing, and reverse-proxy `/api/` to the backend on port 8000.
4. Point the ESP32 firmware's `API_BASE_URL` (in `esp32/HealTheCrop_Firmware/config.h`) at
   your server's public/LAN address.

## Database migrations

```bash
cd backend
alembic upgrade head        # apply all migrations
alembic revision --autogenerate -m "description"   # after changing SQLAlchemy models
```

## Environment variables reference

See [`backend/.env.example`](../backend/.env.example) and
[`frontend/.env.example`](../frontend/.env.example) for the full list. Key ones:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLite for dev, `postgresql+psycopg2://...` for production |
| `JWT_SECRET_KEY` | Must be a long random secret in production |
| `MINIO_ENDPOINT` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | Object storage credentials |
| `CORS_ORIGINS` | JSON list of allowed frontend origins |
| `VITE_API_BASE_URL` (frontend) | Backend API base URL the SPA calls |

## Health checks

- Backend: `GET /health` returns `{"status": "ok", "storage_backend": "minio" | "local_disk_fallback"}`.
- Frontend: served as a static PWA; no server-side health endpoint needed.
