# Deploy VORA Django on Render

This guide deploys the **Geo / Optimization** service as a Docker Web Service on Render with PostGIS support.

## Prerequisites

- Render account: https://render.com
- PostgreSQL database with **PostGIS** enabled (you already have `voora_db` on Frankfurt)
- Google Maps API key with **Geocoding** and **Directions** APIs enabled

---

## Option A — One-click Blueprint (recommended)

1. Push `Backend_django` to GitHub
2. In Render Dashboard → **New** → **Blueprint**
3. Connect the repo — Render reads `render.yaml`
4. Set these **manual env vars** when prompted:
   - `DATABASE_URL` — your Render Postgres connection string
   - `GOOGLE_MAPS_API_KEY`
   - `CORS_ALLOWED_ORIGINS` — e.g. `https://your-app.vercel.app`
   - `CSRF_TRUSTED_ORIGINS` — same + your Render URL
5. Click **Apply** — Render builds the Docker image and deploys

---

## Option B — Manual Web Service setup

### 1. Create Web Service

| Setting | Value |
|---------|-------|
| **Environment** | Docker |
| **Region** | Frankfurt (same as DB) |
| **Branch** | `main` |
| **Root Directory** | `Backend_django` (if monorepo) or repo root |
| **Dockerfile Path** | `./Dockerfile` |
| **Health Check Path** | `/api/v1/health` |

### 2. Environment variables

Set in Render Dashboard → **Environment**:

| Key | Value | Notes |
|-----|-------|-------|
| `DATABASE_URL` | `postgresql://...` | From Render Postgres → **Connections** |
| `SECRET_KEY` | random 50+ char string | Render can auto-generate |
| `DEBUG` | `False` | Required in production |
| `GOOGLE_MAPS_API_KEY` | your key | Required for geo endpoints |
| `ALLOWED_HOSTS` | `localhost,.onrender.com` | `.onrender.com` covers Render URL |
| `CORS_ALLOWED_ORIGINS` | `https://your-frontend.vercel.app` | Comma-separated |
| `CSRF_TRUSTED_ORIGINS` | `https://your-service.onrender.com,https://your-frontend.vercel.app` | Include Render HTTPS URL |
| `TRAJECTORY_TOLERANCE_METERS` | `500` | Optional |
| `WEB_CONCURRENCY` | `2` | Gunicorn workers |
| `GUNICORN_TIMEOUT` | `120` | PostGIS queries can be slow |

> Render auto-sets `RENDER_EXTERNAL_HOSTNAME` and `PORT` — do not override these.

### 3. Link database

If using Render Postgres:
- Copy **External Database URL** (for local) or **Internal** (service-to-service on Render)
- Paste as `DATABASE_URL`

Ensure PostGIS is enabled (already done via Django migration `CreateExtension('postgis')`).

### 4. Deploy

Render will:
1. Build Docker image (installs GDAL/GEOS for GeoDjango)
2. Run `collectstatic`
3. On start: `migrate` → `gunicorn`

---

## Verify deployment

```bash
# Health check
curl https://YOUR-SERVICE.onrender.com/api/v1/health

# Swagger UI
open https://YOUR-SERVICE.onrender.com/api/v1/docs/

# Zones
curl https://YOUR-SERVICE.onrender.com/api/v1/zones
```

Expected health response:

```json
{"status": "ok", "service": "vora-django-geo"}
```

---

## Frontend env vars

Point your React PWA to the deployed service:

```env
VITE_API_GEO_URL=https://YOUR-SERVICE.onrender.com
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `GDAL library not found` | Use **Docker** deploy (Dockerfile installs GDAL) — native Python on Render lacks GeoDjango libs |
| `DisallowedHost` | Add your `*.onrender.com` host to `ALLOWED_HOSTS` or rely on `RENDER_EXTERNAL_HOSTNAME` |
| `SSL connection required` | `DATABASE_URL` must use Render Postgres with `sslmode=require` (auto-included) |
| Cold start slow (free tier) | Normal on free plan — health check wakes the service |
| Migrations fail | Check `DATABASE_URL` is set before first deploy; run manually via Render Shell: `python manage.py migrate` |

---

## Render Shell (manual commands)

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py spectacular --file docs/openapi-schema.json
```

---

## Files reference

| File | Purpose |
|------|---------|
| `Dockerfile` | Python 3.12 + GDAL/GEOS + Gunicorn |
| `render.yaml` | Blueprint for automated deploy |
| `scripts/entrypoint.sh` | Migrate on boot + start Gunicorn |
| `build.sh` | Native build fallback (no GeoDjango) |
| `.dockerignore` | Keeps image small |
