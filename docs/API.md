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
python manage.py migrate
python manage.py seed_vora   # also runs automatically on Render deploy
python manage.py runserver
```

Then open **http://localhost:8000/api/v1/docs/** in your browser.

**Production base URL:** `https://vora-ujbv.onrender.com/api/v1`

---

## Test seed data (Cameroon)

Load realistic Yaoundé & Douala data for frontend / QA:

```bash
python manage.py seed_vora          # upsert seed users & geo data
python manage.py seed_vora --flush  # delete previous seed users first
```

On **Render**, `seed_vora` runs automatically after each deploy (entrypoint, no `--flush` — upserts only).

| Entity | Count |
|--------|-------|
| Passengers | 50 |
| Drivers (taximen jaunes) | 10 |
| Carrefours | 32 |
| Corridor lines | 6 |

**Password for all seed accounts:** `pass12345`  
**OTP (auth simulation):** always `1234`

### Sample sign-in accounts

| Role | Email | City |
|------|-------|------|
| Passenger | `marie.ebanda@gmail.com` | Yaoundé |
| Passenger | `marcel.ebongue@gmail.com` | Douala |
| Driver | `alain.mvondo@vora.cm` | Yaoundé |
| Driver | `dieudonne.tcheuffa@vora.cm` | Douala |

```bash
curl -X POST http://localhost:8000/api/v1/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"marie.ebanda@gmail.com","password":"pass12345"}'
```

---

## Auth (simulation — OTP toujours `1234`)

| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/auth/signup` | Non |
| POST | `/auth/otp/send` | Non |
| POST | `/auth/otp/verify` | Non — utilise **`1234`** |
| POST | `/auth/signin` | Non |
| GET | `/auth/me` | Bearer JWT |

### Flow frontend

1. `POST /auth/signup` avec `role`: `passenger` ou `driver`
2. `POST /auth/otp/verify` avec `{ "email": "...", "otp": "1234" }`
3. `POST /auth/signin` ou utiliser le `access_token` de l'étape 2
4. Header: `Authorization: Bearer <access_token>`

---

## Rides, Driver, Safety

| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/rides/estimate` | Bearer |
| POST | `/rides/request` | Bearer |
| GET | `/rides/{ride_id}/status` | Bearer |
| POST | `/rides/{ride_id}/payment` | Bearer — pay at arrival (simulation) |
| POST | `/rides/{ride_id}/rate` | Bearer — rate + tip (simulation) |
| POST | `/driver/status` | Bearer |
| POST | `/driver/corridor` | Bearer — `corridor_id`: `Y1`, `Y2`, `D1`, etc. |
| PATCH | `/driver/cabin-seats/{seat_id}` | Bearer |
| POST | `/driver/withdraw` | Bearer |
| GET | `/drivers/online` | Public — optional `?city=Yaoundé` |
| POST | `/safety/sos` | Bearer |

---

## Payments (simulation — no real money)

| Method | Endpoint | Notes |
|--------|----------|-------|
| POST | `/payments/mtn-momo` | Simulated MTN MoMo — always confirms |
| POST | `/payments/orange-money` | Simulated Orange Money |
| POST | `/payments/cash/confirm` | Driver/passenger cash confirm |
| GET | `/payments/{transaction_id}/status` | Poll status |
| POST | `/webhooks/mtn-momo` | Simulated provider callback |
| POST | `/webhooks/orange-money` | Simulated provider callback |

All payment responses include `"simulation": true` — **no real FCFA is moved**.

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

### Zones, Carrefours & Corridors

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/api/v1/zones` | List active zones |
| GET | `/api/v1/zones/{id}` | Zone detail + boundary |
| GET | `/api/v1/carrefours` | Optional `?zone_id=` or `?city=Yaoundé` |
| POST | `/api/v1/carrefours` | Admin — create carrefour |
| GET | `/api/v1/corridors` | Optional `?city=Douala` — urban taxi lines |

**GET /api/v1/corridors** response (excerpt):

```json
{
  "success": true,
  "count": 6,
  "data": [
    {
      "id": "Y1",
      "code": "YDE-COR-01",
      "city": "Yaoundé",
      "name": "Ligne Principale Bastos - Poste",
      "start_point": "Poste Centrale",
      "end_point": "Rond-point Bastos",
      "stops": ["Poste Centrale", "Carrefour Warda", "Rond-point Bastos"],
      "standard_fare_fcfa": 500,
      "distance_km": 4.8,
      "estimated_duration_min": 15
    }
  ]
}
```

**GET /api/v1/drivers/online** response (excerpt):

```json
{
  "success": true,
  "count": 8,
  "data": [
    {
      "id": "usr_42",
      "username": "taxi_alain_mvondo",
      "email": "alain.mvondo@vora.cm",
      "full_name": "Alain Mvondo",
      "city": "Yaoundé",
      "license_plate": "LT 482 CE",
      "corridor_line": "Poste Centrale ↔ Bastos",
      "available_seats": 1,
      "status": "ONLINE",
      "location": {"lat": 3.8745, "lng": 11.516}
    }
  ]
}
```

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
python manage.py test geolocation.tests.test_api payments.tests.test_simulation -v 2
```

---

## Cross-service integration

| Caller | Callee | Endpoint |
|--------|--------|----------|
| Spring Boot | Django | `POST /api/v1/geo/verify-destination` |
| Spring Boot | Django | `POST /api/v1/optimize/turn` (optional) |
| Django | Spring Boot | Sync pending reservations → `demand_cache` table |
| Frontend | Django | Zones, geocoding, carrefours, corridors, online drivers |
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
