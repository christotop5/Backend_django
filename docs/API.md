# VORA Django API — Swagger & Testing Guide

Interactive API documentation is auto-generated from the Django REST Framework views.

## Swagger UI

| Resource | URL |
|----------|-----|
| **Swagger UI** | [`http://localhost:8000/api/v1/docs/`](http://localhost:8000/api/v1/docs/) |
| **OpenAPI JSON schema** | [`http://localhost:8000/api/v1/schema/`](http://localhost:8000/api/v1/schema/) |

Start the server:

```bash
cd Backend_django
pip install -r requirements.txt
python manage.py runserver
```

Then open **http://localhost:8000/api/v1/docs/** in your browser.

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL + PostGIS connection string |
| `GOOGLE_MAPS_API_KEY` | Yes (geo endpoints) | Google Maps Geocoding & Directions |
| `SECRET_KEY` | Yes | Django secret key |
| `TRAJECTORY_TOLERANCE_METERS` | No | Default corridor buffer (default `500`) |
| `SPRING_BOOT_RESERVATION_SERVICE_URL` | No | Spring Boot base URL for future reservation sync |

---

## Implemented endpoints (Django service)

### Geolocation (Google Maps wrapper)

| Method | Endpoint | Query / Body |
|--------|----------|--------------|
| GET | `/api/v1/geo/geocode` | `?address=Yaoundé` |
| GET | `/api/v1/geo/reverse-geocode` | `?lat=3.848&lng=11.502` |
| GET | `/api/v1/geo/route` | `?origin=3.84,11.50&destination=3.86,11.52` |
| GET | `/api/v1/geo/congestion` | `?zone_id=1` |

### Zones & Carrefours

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/api/v1/zones` | List active zones |
| GET | `/api/v1/zones/{id}` | Zone detail + boundary |
| GET | `/api/v1/carrefours` | Optional `?zone_id=` filter |
| POST | `/api/v1/carrefours` | Admin — create carrefour |

**POST /api/v1/carrefours body:**

```json
{
  "zone_id": 1,
  "name": "Carrefour Mvan",
  "lat": 3.848,
  "lng": 11.502,
  "is_pickup_point": true
}
```

### Driver trajectories

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/api/v1/drivers/{driver_id}/trajectories` | List all |
| POST | `/api/v1/drivers/{driver_id}/trajectories` | Declare new corridor |
| GET | `/api/v1/drivers/{driver_id}/trajectories/active` | Active trajectory |
| PUT | `/api/v1/drivers/{driver_id}/trajectories/{id}` | Update |
| DELETE | `/api/v1/drivers/{driver_id}/trajectories/{id}` | Deactivate (soft) |

**POST trajectory body:**

```json
{
  "name": "Mvan → Centre",
  "points": [
    {"lat": 3.848, "lng": 11.502},
    {"lat": 3.860, "lng": 11.520}
  ],
  "tolerance_meters": 500
}
```

### Optimization

| Method | Endpoint | Notes |
|--------|----------|-------|
| POST | `/api/v1/optimize/turn` | Greedy turn optimizer |
| POST | `/api/v1/geo/verify-destination` | PostGIS corridor check (Spring Boot calls this) |
| GET | `/api/v1/optimize/demand-heatmap` | `?zone_id=1` |

**POST /api/v1/geo/verify-destination** (Spring Boot matching):

```json
{
  "driver_id": 42,
  "destination": {"lat": 3.855, "lng": 11.515},
  "tolerance_meters": 500
}
```

Response:

```json
{
  "verified": true,
  "driver_id": 42,
  "trajectory_id": 7,
  "distance_meters": 120.5,
  "tolerance_meters": 500
}
```

**POST /api/v1/optimize/turn:**

```json
{
  "driver_id": 42,
  "zone_id": 1
}
```

Response:

```json
{
  "driver_id": 42,
  "trajectory_id": 7,
  "turn": [
    {"type": "pickup", "reservation_id": "RES-1", "location": {"lat": 3.84, "lng": 11.50}, "proposed_price": 2500},
    {"type": "dropoff", "reservation_id": "RES-1", "location": {"lat": 3.86, "lng": 11.52}, "proposed_price": 2500}
  ],
  "expected_revenue": 2500,
  "expected_duration_minutes": 10,
  "candidate_count": 3,
  "selected_count": 1
}
```

### Admin (Django-hosted)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/zones` | All zones (incl. inactive) |
| GET | `/api/v1/admin/reports` | Signalements — `?status=open` |
| GET | `/api/v1/admin/stats` | Daily platform stats |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Service health check |

---

## Running tests

Tests use the configured `DATABASE_URL` (PostGIS required). Google Maps calls are mocked.

```bash
python manage.py test geolocation.tests.test_api -v 2
```

Expected output: all tests pass (health, zones, carrefours, trajectories, optimization, geo mocks, admin).

---

## Cross-service integration

| Caller | Callee | Endpoint |
|--------|--------|----------|
| Spring Boot | Django | `POST /api/v1/geo/verify-destination` |
| Spring Boot | Django | `POST /api/v1/optimize/turn` (optional) |
| Django | Spring Boot | Sync pending reservations → `demand_cache` table |
| Frontend | Django | Zones, geocoding, carrefours (reads) |
| All | Node | JWT auth (validate token before protected routes — TODO) |

---

## Algorithm reference

Turn optimization uses the **MVP greedy pipeline** documented in [`02_VORA_Optimization_Architecture.md`](./02_VORA_Optimization_Architecture.md):

1. PostGIS `ST_DWithin` filters `demand_cache` candidates inside the driver's active trajectory corridor.
2. Candidates sorted by `proposed_price` descending.
3. Up to **4 passengers** selected; turn = all pickups then all dropoffs.
4. Result logged in `optimization_runs` table.

---

## Export OpenAPI schema

```bash
python manage.py spectacular --file docs/openapi-schema.json
```

Share `docs/openapi-schema.json` with frontend / Spring Boot teams for client generation.
