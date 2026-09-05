# VORA Django Backend (OptimRoute CM)

Geolocation, optimization, zones, trajectories — PostgreSQL + PostGIS on Render.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env   # set DATABASE_URL + GOOGLE_MAPS_API_KEY
python manage.py migrate
python manage.py runserver
```

## Swagger docs

Open **http://localhost:8000/api/v1/docs/** after starting the server.

Full API reference: [`docs/API.md`](docs/API.md)

## Apps

| App | Responsibility |
|-----|----------------|
| `geolocation` | Google Maps, zones, carrefours, trajectories |
| `optimization` | Turn optimizer, verify-destination, demand heatmap |
| `operations` | Admin stats/reports, health check |
| `accounts` / `core` / `payments` | Shared DB models (auth, business, payments) |

## Tests

```bash
python manage.py test geolocation.tests.test_api -v 2
```

## Shared database

See [`docs/VORA_Shared_Database_Guide.md`](docs/VORA_Shared_Database_Guide.md)
