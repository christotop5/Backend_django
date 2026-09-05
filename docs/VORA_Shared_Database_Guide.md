# VORA — Shared Database Guide

**Single PostgreSQL + PostGIS database used by all backend services.**

| Service | Stack | DB access |
|---------|-------|-----------|
| **Django** (Geo / Optimization) | Python, DRF, GeoDjango | Read + write (schema owner) |
| **Spring Boot** (Reservations) | Java 17, Spring Data JPA | Read + write |
| **Node.js** (Auth & Payment) | Express, JWT | Read + write |
| **Admin Dashboard** | Node or Django aggregator | Read (mostly) |

> **Architecture reference:** [`VORA_ Architecture_and_API_Specification.pdf`](./VORA_%20Architecture_and_API_Specification.pdf)  
> **API contracts:** [`01_VORA_API_Endpoints.md`](./01_VORA_API_Endpoints.md)  
> **Django models (source of truth for current schema):** `Backend_django/`

---

## 1. Connection

### 1.1 Render PostgreSQL instance

| Setting | Value |
|---------|-------|
| **Host** | `dpg-dae8ef740ujc73e88etg-a.frankfurt-postgres.render.com` |
| **Port** | `5432` |
| **Database** | `voora_db` |
| **User** | `voora_db_user` |
| **Password** | Ask the **Django / DB owner** (stored in team secrets — not in git) |
| **SSL** | **Required** (`sslmode=require`) |
| **PostGIS** | **Enabled** (v3.6) — required for geometry columns |

### 1.2 Connection string format

```text
postgresql://voora_db_user:<PASSWORD>@dpg-dae8ef740ujc73e88etg-a.frankfurt-postgres.render.com:5432/voora_db?sslmode=require
```

Set this as `DATABASE_URL` (Django / Node) or split into JDBC vars (Spring Boot).

---

## 2. How to connect (per stack)

### 2.1 Django (already configured)

```bash
cd Backend_django
cp .env.example .env   # paste DATABASE_URL from team secrets
pip install -r requirements.txt
python manage.py migrate   # only run if schema changed — see §5
python manage.py runserver
```

`config/settings.py` uses PostGIS engine: `django.contrib.gis.db.backends.postgis`.

### 2.2 Node.js (Express)

```bash
npm install pg dotenv
```

```javascript
// db.js
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }, // Render requires SSL
});

module.exports = pool;
```

```bash
# .env
DATABASE_URL=postgresql://voora_db_user:<PASSWORD>@dpg-dae8ef740ujc73e88etg-a.frankfurt-postgres.render.com:5432/voora_db?sslmode=require
```

**Tables Node typically owns (writes):** `users`, `roles`, `jwt_blacklist`, `refresh_tokens`, `two_fa_*`, `password_reset_tokens`, `audit_logs`, `payment_links`.

### 2.3 Spring Boot (Java 17)

```properties
# application.properties
spring.datasource.url=jdbc:postgresql://dpg-dae8ef740ujc73e88etg-a.frankfurt-postgres.render.com:5432/voora_db?sslmode=require
spring.datasource.username=voora_db_user
spring.datasource.password=${DATABASE_PASSWORD}
spring.jpa.hibernate.ddl-auto=validate
spring.jpa.properties.hibernate.dialect=org.hibernate.spatial.dialect.postgis.PostgisPG10Dialect
```

Add dependency for PostGIS if you read/write geometry:

```xml
<dependency>
  <groupId>org.hibernate.orm</groupId>
  <artifactId>hibernate-spatial</artifactId>
</dependency>
```

**Important:** use `ddl-auto=validate` (or `none`) — **do not** let Hibernate auto-create/drop tables on the shared DB. Coordinate schema changes with the Django team.

**Tables Spring Boot typically owns (writes):** `reservations` *(see §6 — not created yet)*, `notifications` (ride events), reads from `users`, `driver_trajectories`, `demand_cache`.

### 2.4 psql / GUI (DBeaver, pgAdmin, TablePlus)

```bash
psql "postgresql://voora_db_user:<PASSWORD>@dpg-dae8ef740ujc73e88etg-a.frankfurt-postgres.render.com:5432/voora_db?sslmode=require"
```

Verify PostGIS:

```sql
SELECT PostGIS_Version();
```

---

## 3. Rules for shared DB usage

1. **One database, real foreign keys** — `user_id`, `driver_id`, `client_id`, etc. reference `users.id` / `clients.id` directly.
2. **Schema owner = Django team** — new/changed tables go through Django migrations in `Backend_django/`. Other stacks: **propose changes, don't ALTER manually**.
3. **Never run `DROP` / `TRUNCATE` on shared tables** without team agreement.
4. **Password column is `password_hash`** on `users` (bcrypt/argon2 — Node auth service writes it).
5. **Timestamps are UTC** — Django uses `USE_TZ=True`; store `timestamptz` where possible.
6. **Currency default: XAF** (FCFA).
7. **Geometry SRID = 4326** (WGS84 lat/lng). PostGIS types:
   - `Point` → pickup, destination, driver location
   - `LineString` → driver trajectory corridor
   - `Polygon` → zone boundary
8. **JWT** is issued by Node; other services validate it — they may **read** `users` / `jwt_blacklist` but don't issue tokens.

---

## 4. Table ownership matrix

| Table | Primary writer | Readers |
|-------|----------------|---------|
| `roles` | Node (Auth) | All |
| `users` | Node (Auth) | All |
| `jwt_blacklist` | Node (Auth) | Django, Spring |
| `refresh_tokens` | Node (Auth) | Node |
| `two_fa_otp_codes` | Node (Auth) | Node |
| `two_fa_totp` | Node (Auth) | Node |
| `password_reset_tokens` | Node (Auth) | Node |
| `audit_logs` | All services | Admin |
| `parametres` | Admin / Node | All |
| `clients` | Node / Spring | All |
| `vehicles` | Admin / Spring | All |
| `routes` | Django / Spring | All |
| `orders` | Spring | Node (payments) |
| `payment_links` | Node (Payment) | All |
| `zones` | Django | All |
| `carrefours` | Django | All |
| `driver_trajectories` | Django | Spring, Django |
| `driver_locations` | Django / Spring | All (WebSocket feed) |
| `congestion_snapshots` | Django | All |
| `demand_cache` | Django (sync from Spring) | Django |
| `optimization_runs` | Django | Admin |
| `notifications` | Spring / Django | All |
| `historique_activite` | All | Admin |
| `signalements` | All | Admin |
| `statistiques_journalieres` | Cron / Admin | Admin |

---

## 5. Live schema (27 domain tables)

All tables below **already exist** on Render (migrated September 2025).

### 5.1 Auth & identity — Node.js

#### `roles`
| Column | Type | Notes |
|--------|------|-------|
| id | smallint (PK) | |
| name | varchar(50) UNIQUE | e.g. `ADMIN`, `DRIVER`, `CLIENT`, `MANAGER` |
| description | varchar(255) | nullable |
| permissions | jsonb | default `{}` |
| is_active | boolean | default true |
| created_at / updated_at | timestamptz | |

#### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | **Use this ID everywhere as `user_id` / `driver_id`** |
| role_id | FK → roles.id | |
| first_name / last_name | varchar(100) | |
| email | varchar(191) UNIQUE | login identifier |
| phone | varchar(30) UNIQUE | nullable |
| password_hash | varchar(255) | bcrypt hash — column name is `password_hash` |
| is_active / is_email_verified / is_phone_verified | boolean | |
| failed_login_attempts | smallint | default 0 |
| locked_until | timestamptz | nullable |
| last_login_at / last_login_ip | timestamptz / inet | nullable |
| two_fa_enabled | boolean | |
| two_fa_method | varchar(10) | `TOTP`, `SMS`, `email` |
| created_at / updated_at / deleted_at | timestamptz | soft delete via `deleted_at` |

#### `jwt_blacklist`
| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | |
| jti | varchar(64) UNIQUE | revoked JWT id |
| user_id | FK → users.id | |
| expires_at | timestamptz | |
| reason | varchar(100) | nullable |

#### `refresh_tokens`
| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | |
| user_id | FK → users.id | |
| token_hash | varchar(255) UNIQUE | SHA-256 |
| client_type | varchar(20) | `dashboard`, `mobile` |
| device_name / device_fingerprint | varchar | nullable |
| ip_address / user_agent | inet / text | nullable |
| expires_at / revoked_at | timestamptz | |
| revoke_reason | varchar(100) | nullable |

#### `two_fa_otp_codes` / `two_fa_totp` / `password_reset_tokens`
Standard 2FA and password-reset tables — see Django models in `Backend_django/accounts/models.py`.

#### `audit_logs`
| Column | Type | Notes |
|--------|------|-------|
| user_id | FK → users.id | nullable |
| action | varchar(100) | e.g. `login`, `logout` |
| resource / resource_id | varchar | nullable |
| client_type | varchar(20) | `dashboard`, `mobile`, `api`, `system`, `odoo_auth` |

#### `parametres`
App-wide config key/value store (`cle`, `valeur`, `type`).

---

### 5.2 Business — Spring Boot / shared

#### `clients`
| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | |
| user_id | FK → users.id | nullable OneToOne |
| company_name | varchar(150) | nullable |
| contact_name / email / phone | varchar | |
| address | text | nullable |
| city | varchar(100) | default `Douala` |

#### `vehicles`
| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| registration_number | varchar(30) UNIQUE | plate number |
| model | varchar(100) | |
| capacity_kg / volume_m3 | decimal | |
| status | varchar(20) | `AVAILABLE`, `IN_TRANSIT`, `MAINTENANCE` |
| assigned_driver_id | FK → users.id | nullable |

#### `routes`
| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | |
| driver_id | FK → users.id | |
| vehicle_id | FK → vehicles.id | |
| status | varchar(20) | `DRAFT`, `OPTIMIZED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` |
| optimized_geometry | jsonb | GeoJSON waypoints |
| total_distance_km / estimated_duration_min | decimal / int | |
| started_at / completed_at | timestamptz | nullable |

#### `orders`
| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | |
| tracking_number | varchar(64) UNIQUE | |
| client_id | FK → clients.id | |
| route_id | FK → routes.id | nullable |
| delivery_address | text | |
| latitude / longitude | decimal | nullable (non-PostGIS fallback) |
| status | varchar(20) | `PENDING`, `ASSIGNED`, `IN_TRANSIT`, `DELIVERED`, `FAILED` |
| amount_to_collect | decimal(10,2) | COD amount |

---

### 5.3 Payments — Node.js

#### `payment_links`
| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| token | varchar(255) UNIQUE | public payment URL token |
| client_id | FK → clients.id | |
| order_id | FK → orders.id | nullable |
| amount | decimal(10,2) | |
| devise | varchar(10) | default `XAF` |
| langue | varchar(5) | default `fr` |
| canal_envoi | varchar(10) | `mail`, `sms` |
| moyen_paiement | varchar(15) | `mtn`, `orange`, `carte`, `autre` |
| status | varchar(15) | `pending`, `paid`, `expired`, `failed` |
| soleaspay_ref | varchar(255) | gateway transaction id |

---

### 5.4 Geolocation — Django (PostGIS)

#### `zones`
| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| name | varchar(100) | e.g. `Mimboman`, `Kondengui` |
| boundary | geometry(Polygon, 4326) | nullable |
| is_active | boolean | |

#### `carrefours`
| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| zone_id | FK → zones.id | nullable |
| name | varchar(150) | local junction name |
| location | geometry(Point, 4326) | **NOT NULL** |
| is_pickup_point | boolean | default true |

#### `driver_trajectories`
| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | |
| driver_id | FK → users.id | |
| name | varchar(150) | nullable |
| geometry | geometry(LineString, 4326) | declared work corridor |
| tolerance_meters | int | default **500** — used in `ST_DWithin` matching |
| is_active | boolean | |

**Example corridor filter (from architecture spec):**

```sql
SELECT dc.*
FROM demand_cache dc
JOIN driver_trajectories dt ON dt.driver_id = :driver_id AND dt.is_active = true
WHERE ST_DWithin(
  dc.destination_location::geography,
  dt.geometry::geography,
  dt.tolerance_meters
);
```

#### `driver_locations`
Live GPS pings: `driver_id`, `location` (Point 4326), `speed`, `heading`, `recorded_at`.

Indexed on `(driver_id, recorded_at DESC)` — use for WebSocket `/topic/reservations/{id}/driver-location`.

#### `congestion_snapshots`
`zone_id`, `congestion_level` (`low` / `medium` / `high`), `source`, `recorded_at`.

---

### 5.5 Optimization — Django

#### `demand_cache`
Mirror of pending reservations for the turn optimizer (synced from Spring Boot).

| Column | Type | Notes |
|--------|------|-------|
| reservation_id | varchar(64) UNIQUE | **Spring Boot reservation PK / UUID as string** |
| pickup_location | Point 4326 | |
| destination_location | Point 4326 | |
| proposed_price | decimal(10,2) | |
| status | varchar(30) | synced status |
| fetched_at | timestamptz | last sync time |

#### `optimization_runs`
Audit log of each `/api/v1/optimize/turn` call: `input_snapshot` (jsonb), `output_turn` (jsonb), `expected_revenue`.

---

### 5.6 Operations — shared

#### `notifications`
In-app alerts: `user_id`, `type`, `title`, `message`, `is_read`, `created_at`.

#### `historique_activite`
Activity log: `user_id`, `driver_id`, `event_type`, `reference_id`, `metadata` (jsonb).

#### `signalements`
Safety reports: `reporter_id`, `reported_user_id`, `reservation_id`, `type` (`sos`/`complaint`/`anomaly`), `status`, `location` (Point), `resolved_at`.

#### `statistiques_journalieres`
Daily aggregates: `date` (UNIQUE), `total_rides`, `total_revenue`, `active_drivers`, `active_zones`.

---

## 6. Entity relationship (simplified)

```text
roles ──< users ──< refresh_tokens / jwt_blacklist / two_fa_* / notifications
              │
              ├──< driver_trajectories / driver_locations / optimization_runs
              ├──< routes >── vehicles
              └── o── clients ──< orders ──< payment_links
zones ──< carrefours
zones ──< congestion_snapshots
demand_cache  (reservation_id → external reservations table)
signalements  (reservation_id → external reservations table)
```

---

## 7. Cross-service data flows

| Flow | Writer | Reader | Table(s) |
|------|--------|--------|----------|
| User registers / logs in | Node | All | `users`, `roles`, `refresh_tokens` |
| Driver declares corridor | Django | Spring | `driver_trajectories` |
| Passenger books ride | Spring | Django | `reservations` *(TBD)* → `demand_cache` |
| Corridor matching | Django | — | PostGIS on `driver_trajectories` + `demand_cache` |
| Live GPS | Spring/Django | Frontend (WS) | `driver_locations` |
| Payment after arrival | Node | Spring | `payment_links`, `orders` |
| SOS / complaint | Any | Admin | `signalements` |
| Daily stats | Cron | Admin | `statistiques_journalieres` |

---

## 8. Pending: `reservations` table (Spring Boot)

The [architecture PDF](./VORA_%20Architecture_and_API_Specification.pdf) and Spring Boot API spec assume a **`reservations`** table. It is **not yet created** in the shared DB.

**Spring Boot team:** propose the schema (pickup/destination points, status enum, `passenger_id`, `driver_id`, `proposed_price`, etc.) and coordinate with Django to add it via migration **or** add a Spring migration file reviewed by the team.

Suggested minimum columns:

| Column | Type | Notes |
|--------|------|-------|
| id | bigint or UUID | PK |
| passenger_id | FK → users.id | |
| driver_id | FK → users.id | nullable until accepted |
| pickup_location | Point 4326 | |
| destination_location | Point 4326 | |
| proposed_price | decimal(10,2) | |
| status | varchar(30) | `EN_ATTENTE`, `ACCEPTEE`, `EN_COURS`, `TERMINEE`, `ANNULEE` |
| created_at / updated_at | timestamptz | |

Once live, Django syncs pending rows into `demand_cache.reservation_id`.

---

## 9. Seed data (recommended)

Run once after first deploy:

```sql
INSERT INTO roles (name, description, permissions, is_active, created_at, updated_at)
VALUES
  ('ADMIN',   'Platform administrator', '{}', true, NOW(), NOW()),
  ('DRIVER',  'Taxi driver',            '{}', true, NOW(), NOW()),
  ('CLIENT',  'Passenger / client',     '{}', true, NOW(), NOW()),
  ('MANAGER', 'Fleet manager',          '{}', true, NOW(), NOW())
ON CONFLICT (name) DO NOTHING;
```

Zone/carrefour seed data for Yaoundé should be loaded by the Django team.

---

## 10. Schema changes checklist

When any team needs a new column or table:

1. Open issue / Slack message describing the change.
2. Django team adds model + migration in `Backend_django/`.
3. Run `python manage.py migrate` on Render (or CI).
4. Other teams update their ORM entities to match.
5. Update **this document**.

---

## 11. Quick reference — env vars

| Service | Variable | Example |
|---------|----------|---------|
| Django | `DATABASE_URL` | full connection string |
| Node | `DATABASE_URL` | full connection string |
| Spring Boot | `SPRING_DATASOURCE_URL` | JDBC URL with `sslmode=require` |
| Spring Boot | `SPRING_DATASOURCE_USERNAME` | `voora_db_user` |
| Spring Boot | `SPRING_DATASOURCE_PASSWORD` | from team secrets |
| All | `JWT_SECRET` | shared across services for token validation |

---

## 12. Contacts

| Role | Responsibility |
|------|----------------|
| **Django team** | Schema migrations, PostGIS, zones, trajectories, optimization |
| **Node team** | Auth tables, payment_links, user registration |
| **Spring Boot team** | Reservations lifecycle, WebSocket GPS, notifications |

For database credentials, contact the **Django / infrastructure owner**.
