# OptimRoute CM — Data Dictionary (Django Geolocation & Optimization Module)

Consolidated reference for the Django side of the backend: the tables the wider team has already defined (Auth, Payment) plus the tables needed to implement geolocation, carrefours, congestion, optimization, notifications, historique, sécurité, and statistiques — the modules assigned to this side of the project.

## How to use this file (for Cursor)

- All geometry fields use **PostGIS** via **GeoDjango**: `django.contrib.gis.db.models` with `PointField`, `LineStringField`, `PolygonField`, all at **SRID 4326**.
- `Part A` tables already exist (owned by the Auth/Payment side). Model them as regular Django models mapped with `db_table` to the existing table names. If the project uses **one shared database**, set them up as normal models; if each service actually gets its **own database** (per the deployment architecture doc), model only the FK columns you need locally and treat the rest as external references resolved via API instead of a live FK constraint — confirm with the team which setup is actually in place before generating migrations for Part A.
- `Part B` tables are new — these are yours to create migrations for.
- Recommended Django app layout: `geolocation/` (zones, carrefours, driver_trajectories, driver_locations, congestion_snapshots), `optimization/` (optimization_runs, demand_cache), `operations/` (notifications, historique_activite, signalements, statistiques_journalieres).

---

## Part A — Existing Tables (Reference / Shared)

### Authentification JWT

| Table | Field | Type | Constraints | Description |
|---|---|---|---|---|
| roles | id | TINYINT UNSIGNED | PK, AUTO_INCREMENT | Identifiant unique du rôle |
| roles | name | VARCHAR(50) | NOT NULL, UNIQUE | Nom du rôle |
| roles | description | VARCHAR(255) | NULL | Description du rôle |
| roles | permissions | JSON | NOT NULL | Permissions associées au rôle |
| roles | is_active | BOOLEAN | NOT NULL, default 1 | Rôle actif |
| roles | created_at / updated_at | DATETIME | NOT NULL | Horodatage |
| users | id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | Identifiant unique de l'utilisateur |
| users | role_id | TINYINT UNSIGNED | FK → roles.id, NOT NULL | Rôle attribué |
| users | first_name / last_name | VARCHAR(100) | NOT NULL | Nom/prénom |
| users | email | VARCHAR(191) | NOT NULL, UNIQUE | Email d'identification |
| users | phone | VARCHAR(30) | UNIQUE, NULL | Téléphone |
| users | password_hash | VARCHAR(255) | NOT NULL | Hash bcrypt |
| users | is_active / is_email_verified / is_phone_verified | BOOLEAN | NOT NULL | Statuts du compte |
| users | failed_login_attempts | TINYINT UNSIGNED | NOT NULL | Tentatives échouées |
| users | locked_until | DATETIME | NULL | Verrouillage temporaire |
| users | last_login_at / last_login_ip | DATETIME / VARCHAR(45) | NULL | Dernière connexion |
| users | two_fa_enabled | BOOLEAN | NOT NULL | 2FA actif |
| users | two_fa_method | ENUM(TOTP, SMS, email) | NULL | Méthode 2FA |
| users | created_at / updated_at / deleted_at | DATETIME | — | Horodatage / suppression logique |
| jwt_blacklist | id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | — |
| jwt_blacklist | jti | VARCHAR(64) | NOT NULL, UNIQUE | Identifiant du JWT révoqué |
| jwt_blacklist | user_id | BIGINT UNSIGNED | NOT NULL | Propriétaire |
| jwt_blacklist | expires_at | DATETIME | NOT NULL | Expiration |
| jwt_blacklist | reason | VARCHAR(100) | NULL | Motif |
| jwt_blacklist | created_at | DATETIME | NOT NULL | — |
| refresh_tokens | id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | — |
| refresh_tokens | user_id | BIGINT UNSIGNED | FK → users.id | — |
| refresh_tokens | token_hash | VARCHAR(255) | NOT NULL, UNIQUE | Hash SHA-256 |
| refresh_tokens | client_type | ENUM(dashboard, mobile) | NOT NULL | — |
| refresh_tokens | device_name / device_fingerprint | VARCHAR | NULL | — |
| refresh_tokens | ip_address / user_agent | VARCHAR(45) / TEXT | NULL | — |
| refresh_tokens | expires_at / revoked_at | DATETIME | NULL for revoked_at | — |
| refresh_tokens | revoke_reason | VARCHAR(100) | NULL | — |
| refresh_tokens | created_at | DATETIME | NOT NULL | — |
| two_fa_otp_codes | id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | — |
| two_fa_otp_codes | user_id | BIGINT UNSIGNED | FK → users.id | — |
| two_fa_otp_codes | channel | ENUM(SMS, email) | NOT NULL | — |
| two_fa_otp_codes | code_hash | VARCHAR(255) | NOT NULL | — |
| two_fa_otp_codes | purpose | ENUM(login, password_reset, email_verify, phone_verify) | NOT NULL | — |
| two_fa_otp_codes | expires_at / used_at | DATETIME | NULL for used_at | — |
| two_fa_otp_codes | attempts | TINYINT UNSIGNED | NOT NULL | — |
| two_fa_otp_codes | ip_address / created_at | VARCHAR(45) / DATETIME | — | — |
| two_fa_totp | id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | — |
| two_fa_totp | user_id | BIGINT UNSIGNED | FK → users.id, UNIQUE | — |
| two_fa_totp | secret | VARCHAR(64) | NOT NULL | Secret chiffré |
| two_fa_totp | backup_codes | JSON | NOT NULL | Codes de récupération |
| two_fa_totp | is_confirmed | BOOLEAN | NOT NULL | — |
| two_fa_totp | created_at / updated_at | DATETIME | — | — |
| password_reset_tokens | id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | — |
| password_reset_tokens | user_id | BIGINT UNSIGNED | FK → users.id | — |
| password_reset_tokens | token_hash | VARCHAR(255) | NOT NULL, UNIQUE | — |
| password_reset_tokens | expires_at / used_at | DATETIME | NULL for used_at | — |
| password_reset_tokens | ip_address / created_at | VARCHAR(45) / DATETIME | — | — |
| audit_logs | id | BIGINT UNSIGNED | PK | — |
| audit_logs | user_id | BIGINT UNSIGNED | NULL | — |
| audit_logs | action | VARCHAR(100) | NOT NULL | login, logout, etc. |
| audit_logs | resource / resource_id | VARCHAR | NULL for resource_id | Table/entité concernée |
| audit_logs | ip_address / user_agent | VARCHAR(45) / TEXT | NULL | — |
| audit_logs | client_type | ENUM(dashboard, mobile, api, system, odoo_auth) | NOT NULL | — |
| audit_logs | created_at | DATETIME | NOT NULL | — |
| parametres | id | INT UNSIGNED | PK, AUTO_INCREMENT | — |
| parametres | cle | VARCHAR(100) | NOT NULL, UNIQUE | Clé du paramètre |
| parametres | valeur | TEXT | NULL | — |
| parametres | type | ENUM(string, integer, boolean, json, secret) | NOT NULL | — |
| parametres | description | VARCHAR(255) | NULL | — |
| parametres | updated_by / updated_at | BIGINT UNSIGNED / DATETIME | NULL for updated_by | — |

### Paiement

| Table | Field | Type | Constraints | Description |
|---|---|---|---|---|
| payment_links | id | INT(11) | PK, NOT NULL | — |
| payment_links | token | VARCHAR(255) | NOT NULL | Jeton d'accès au lien |
| payment_links | client_id | BIGINT UNSIGNED | NOT NULL, FK → clients/users.id | — |
| payment_links | amount | DECIMAL(10,2) | NOT NULL | — |
| payment_links | devise | VARCHAR(10) | default XAF | — |
| payment_links | langue | VARCHAR(5) | default fr | — |
| payment_links | description | TEXT | NULL | — |
| payment_links | canal_envoi | ENUM(mail, sms) | — | — |
| payment_links | moyen_paiement | ENUM(mtn, orange, carte, autre) | — | — |
| payment_links | status | ENUM(pending, paid, expired, failed) | — | — |
| payment_links | soleaspay_ref | VARCHAR(255) | NULL | Référence transaction |
| payment_links | created_at | TIMESTAMP | NOT NULL, default CURRENT_TIMESTAMP | — |

---

## Part B — New Tables (Django Geolocation & Optimization Module)

### `zones` — Reference urban zones (e.g. taxi catchment areas)

| Field | Type | Constraints | Description |
|---|---|---|---|
| id | INT | PK, AUTO_INCREMENT | — |
| name | VARCHAR(100) | NOT NULL | Nom de la zone (e.g. "Mimboman", "Kondengui") |
| description | VARCHAR(255) | NULL | — |
| boundary | POLYGON (SRID 4326) | NULL | Contour géographique de la zone |
| is_active | BOOLEAN | NOT NULL, default TRUE | — |
| created_at / updated_at | DATETIME | NOT NULL | — |

### `carrefours` — Junctions / known pickup-drop reference points

| Field | Type | Constraints | Description |
|---|---|---|---|
| id | INT | PK, AUTO_INCREMENT | — |
| zone_id | INT | FK → zones.id, NULL | Zone à laquelle appartient le carrefour |
| name | VARCHAR(150) | NOT NULL | Nom local du carrefour |
| location | POINT (SRID 4326) | NOT NULL | Coordonnées |
| is_pickup_point | BOOLEAN | NOT NULL, default TRUE | Utilisable comme point de ramassage |
| created_at / updated_at | DATETIME | NOT NULL | — |

### `driver_trajectories` — Declared work "turns" per driver

| Field | Type | Constraints | Description |
|---|---|---|---|
| id | BIGINT | PK, AUTO_INCREMENT | — |
| driver_id | BIGINT UNSIGNED | FK → users.id, NOT NULL | Chauffeur propriétaire |
| name | VARCHAR(150) | NULL | Nom donné au trajet |
| geometry | LINESTRING (SRID 4326) | NOT NULL | Trajectoire déclarée |
| tolerance_meters | INT | NOT NULL, default 500 | Tolérance de matching |
| is_active | BOOLEAN | NOT NULL, default TRUE | — |
| created_at / updated_at | DATETIME | NOT NULL | — |

### `driver_locations` — Live GPS pings

| Field | Type | Constraints | Description |
|---|---|---|---|
| id | BIGINT | PK, AUTO_INCREMENT | — |
| driver_id | BIGINT UNSIGNED | FK → users.id, NOT NULL | — |
| location | POINT (SRID 4326) | NOT NULL | Position actuelle |
| speed | DECIMAL(5,2) | NULL | km/h |
| heading | DECIMAL(5,2) | NULL | Degrés (0–360) |
| recorded_at | DATETIME | NOT NULL | — |

### `congestion_snapshots` — Traffic/congestion readings per zone

| Field | Type | Constraints | Description |
|---|---|---|---|
| id | BIGINT | PK, AUTO_INCREMENT | — |
| zone_id | INT | FK → zones.id, NOT NULL | — |
| congestion_level | ENUM(low, medium, high) | NOT NULL | — |
| source | VARCHAR(50) | NULL | e.g. "google_maps", "heuristic" |
| recorded_at | DATETIME | NOT NULL | — |

### `demand_cache` — Local cache of pending reservations (pulled from the Spring Boot reservation service for optimization)

| Field | Type | Constraints | Description |
|---|---|---|---|
| id | BIGINT | PK, AUTO_INCREMENT | — |
| reservation_id | VARCHAR(64) | NOT NULL, UNIQUE | ID externe (service Réservation) |
| pickup_location | POINT (SRID 4326) | NOT NULL | — |
| destination_location | POINT (SRID 4326) | NOT NULL | — |
| proposed_price | DECIMAL(10,2) | NOT NULL | — |
| status | VARCHAR(30) | NOT NULL | Statut synchronisé |
| fetched_at | DATETIME | NOT NULL | Dernière synchronisation |

### `optimization_runs` — Log of each "turn" computation (useful for the jury demo)

| Field | Type | Constraints | Description |
|---|---|---|---|
| id | BIGINT | PK, AUTO_INCREMENT | — |
| driver_id | BIGINT UNSIGNED | FK → users.id, NOT NULL | — |
| input_snapshot | JSON | NOT NULL | Candidats de demande au moment du calcul |
| output_turn | JSON | NOT NULL | Séquence de pickups/drops retournée |
| expected_revenue | DECIMAL(10,2) | NULL | — |
| created_at | DATETIME | NOT NULL | — |

### `notifications` — In-app notifications

| Field | Type | Constraints | Description |
|---|---|---|---|
| id | BIGINT | PK, AUTO_INCREMENT | — |
| user_id | BIGINT UNSIGNED | FK → users.id, NOT NULL | — |
| type | VARCHAR(50) | NOT NULL | e.g. "new_offer", "ride_started" |
| title | VARCHAR(150) | NOT NULL | — |
| message | TEXT | NOT NULL | — |
| is_read | BOOLEAN | NOT NULL, default FALSE | — |
| created_at | DATETIME | NOT NULL | — |

### `historique_activite` — Generic activity/trip history (for stats & admin dashboard)

| Field | Type | Constraints | Description |
|---|---|---|---|
| id | BIGINT | PK, AUTO_INCREMENT | — |
| user_id | BIGINT UNSIGNED | FK → users.id, NULL | — |
| driver_id | BIGINT UNSIGNED | FK → users.id, NULL | — |
| event_type | VARCHAR(50) | NOT NULL | e.g. "ride_completed", "trajectory_updated" |
| reference_id | VARCHAR(64) | NULL | ID de la ressource liée (ex. reservation_id) |
| metadata | JSON | NULL | Détails additionnels |
| created_at | DATETIME | NOT NULL | — |

### `signalements` — Security incidents / SOS reports

| Field | Type | Constraints | Description |
|---|---|---|---|
| id | BIGINT | PK, AUTO_INCREMENT | — |
| reporter_id | BIGINT UNSIGNED | FK → users.id, NOT NULL | — |
| reported_user_id | BIGINT UNSIGNED | FK → users.id, NULL | — |
| reservation_id | VARCHAR(64) | NULL | — |
| type | ENUM(sos, complaint, anomaly) | NOT NULL | — |
| description | TEXT | NULL | — |
| status | ENUM(open, investigating, resolved, dismissed) | NOT NULL, default 'open' | — |
| location | POINT (SRID 4326) | NULL | — |
| created_at / resolved_at | DATETIME | NULL for resolved_at | — |

### `statistiques_journalieres` — Daily aggregated stats (admin dashboard)

| Field | Type | Constraints | Description |
|---|---|---|---|
| id | BIGINT | PK, AUTO_INCREMENT | — |
| date | DATE | NOT NULL, UNIQUE | — |
| total_rides | INT | NOT NULL, default 0 | — |
| total_revenue | DECIMAL(12,2) | NOT NULL, default 0 | — |
| active_drivers | INT | NOT NULL, default 0 | — |
| active_zones | INT | NOT NULL, default 0 | — |
| created_at | DATETIME | NOT NULL | — |

---

## Open Questions to Settle With the Team (flag before generating migrations)

1. **Shared DB or per-service DB?** This dictionary assumes tables might coexist in one Postgres instance (`OptimRoute CM`), but the deployment plan discussed earlier has Django on its own PostGIS-enabled Postgres, separate from Spring Boot's DB. If they're separate, `driver_id`/`user_id` FKs to `users` can't be real foreign keys — store them as plain IDs and treat `users`/`roles` as external, or expose a small `GET /api/v1/internal/users/{id}` on the auth service for validation instead.
2. **`demand_cache` sync mechanism** — decide whether Django polls Spring Boot's pending-reservations endpoint on an interval, or Spring Boot pushes updates (webhook/queue) into `demand_cache`.
3. **PostGIS extension** — confirm it's enabled on the Render Postgres instance before running the first migration with geometry fields.
