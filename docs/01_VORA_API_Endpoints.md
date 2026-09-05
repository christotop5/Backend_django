# VORA — API Endpoints Reference (All Services)

This document lists every backend endpoint across VORA's microservices, what it does, and which service owns it. Use it as the single source of truth so frontend, Spring Boot, Django, and Node all agree on contracts.

## Services Overview

| Service | Responsibility | Stack | Host |
|---|---|---|---|
| **Django Geo/Optimization Service** | Geolocation, Google Maps integration, driver trajectories, turn optimization, zones/carrefours, congestion | Django + DRF, PostgreSQL + PostGIS | Render |
| **Spring Boot Reservation Service** | Booking lifecycle, matching orchestration, real-time tracking, notifications, payment trigger | Spring Boot 3.x, PostgreSQL | Render (Docker) |
| **Node.js Auth & Payment Service** | Google/email auth, Orange Money, MTN MoMo, cash confirmation | Node.js | Render |
| **Admin Dashboard Backend** | Aggregated management views (may live inside Django or Node — see note) | TBD | Render |
| **Frontend** | Consumes all of the above | React PWA | Vercel |

> Note: keep every response JSON, versioned under `/api/v1/`, and authenticated with the JWT issued by the Node auth service unless stated otherwise.

---

## 1. Django Geo/Optimization Service

### 1.1 Geolocation & Mapping (Google Maps wrapper)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/geo/geocode?address=` | Converts a free-text address (or local landmark) into lat/lng via Google Geocoding API. |
| GET | `/api/v1/geo/reverse-geocode?lat=&lng=` | Converts coordinates back into a human-readable address/landmark. |
| GET | `/api/v1/geo/route?origin=&destination=` | Returns route, distance, ETA between two points via Google Directions API. |
| GET | `/api/v1/geo/congestion?zone_id=` | Returns current congestion/traffic level for a declared zone (if implemented — can start as a simple heuristic). |

### 1.2 Zones & Carrefours (pickup points / intersections)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/zones` | Lists known Yaoundé taxi zones / pickup stations (seeded reference data). |
| GET | `/api/v1/zones/{id}` | Detail of one zone (boundary, name, associated carrefours). |
| GET | `/api/v1/carrefours` | Lists intersections/junctions used as pickup-drop reference points. |
| POST | `/api/v1/carrefours` | (Admin) Add a new carrefour reference point. |

### 1.3 Driver Trajectories ("turns")

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/drivers/{driver_id}/trajectories` | Driver declares a new work trajectory (ordered list of zones/carrefours forming a LineString). |
| GET | `/api/v1/drivers/{driver_id}/trajectories` | List a driver's trajectories (active/inactive). |
| PUT | `/api/v1/drivers/{driver_id}/trajectories/{id}` | Update a trajectory. |
| DELETE | `/api/v1/drivers/{driver_id}/trajectories/{id}` | Deactivate a trajectory. |
| GET | `/api/v1/drivers/{driver_id}/trajectories/active` | Returns the currently active trajectory for a driver (used by matching). |

### 1.4 Optimization & Matching Support

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/optimize/turn` | **Core algorithm.** Given a driver's chosen zone(s) and current live demand (pending reservations), returns the optimal ordered path (turn) that maximizes expected revenue — see the Optimization Architecture doc for the algorithm. |
| POST | `/api/v1/geo/verify-destination` | **Used by Spring Boot during matching.** Given a driver's active trajectory and a client's destination, returns whether the destination is on/near the trajectory within a configurable tolerance (e.g. 500m–1km), using a PostGIS spatial query (`ST_DWithin`). |
| GET | `/api/v1/optimize/demand-heatmap?zone_id=` | Returns current clustered demand points in a zone, for drivers deciding where to work. |

---

## 2. Spring Boot Reservation Service

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/reservations` | Create a reservation: client GPS position, location precision text, destination, proposed price. Triggers matching (calls Django `verify-destination` per candidate driver). |
| GET | `/api/v1/reservations/{id}` | Get reservation detail/status. |
| POST | `/api/v1/reservations/{id}/cancel` | Cancel a reservation. |
| GET | `/api/v1/driver/reservation-offers` | Driver retrieves compatible pending offers. |
| POST | `/api/v1/driver/reservation-offers/{offerId}/accept` | Driver accepts an offer (atomic, first-acceptance-wins with pessimistic locking). |
| POST | `/api/v1/driver/reservations/{id}/start` | Driver marks the ride as started (client onboard). |
| POST | `/api/v1/reservations/{id}/arrival` | Client confirms arrival — triggers payment workflow. |
| POST | `/api/v1/reservations/{id}/payment` | Triggers payment (delegates to Node payment service). |
| GET | `/api/v1/reservations/{id}/payment` | Payment status for a reservation. |
| WS | `/topic/reservations/{reservationId}/driver-location` | STOMP topic broadcasting live driver GPS (lat, lng, speed, heading). |

---

## 3. Node.js Auth & Payment Service

### 3.1 Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Email/password registration. |
| POST | `/api/v1/auth/login` | Email/password login, returns JWT. |
| POST | `/api/v1/auth/google` | Google OAuth sign-in, returns JWT. |
| POST | `/api/v1/auth/refresh` | Refresh an expiring JWT. |
| POST | `/api/v1/auth/logout` | Invalidate refresh token. |
| GET | `/api/v1/auth/me` | Return current authenticated user profile. |

### 3.2 Payments

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/payments/orange-money` | Initiate an Orange Money charge for a reservation amount. |
| POST | `/api/v1/payments/mtn-momo` | Initiate an MTN Mobile Money charge. |
| POST | `/api/v1/payments/cash/confirm` | Mark a cash payment as collected (driver-confirmed). |
| GET | `/api/v1/payments/{id}/status` | Poll payment provider confirmation status. |
| POST | `/api/v1/webhooks/orange-money` | Callback endpoint for Orange Money provider confirmation. |
| POST | `/api/v1/webhooks/mtn-momo` | Callback endpoint for MTN MoMo provider confirmation. |

### 3.3 Email

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/email/send` | Generic transactional email sender (verification, notifications) used internally by other services. |

---

## 4. Admin Dashboard Endpoints

*(Decide as a team whether these live in Django, Node, or a thin dedicated service — listed here as a contract regardless of final host.)*

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/admin/users` | List/manage passenger accounts. |
| GET | `/api/v1/admin/drivers` | List/manage driver accounts + verification status. |
| GET | `/api/v1/admin/vehicles` | List/manage registered vehicles. |
| GET | `/api/v1/admin/reservations` | Monitor rides in progress / history. |
| GET | `/api/v1/admin/reports` | View flagged incidents/reports (SOS, complaints). |
| GET | `/api/v1/admin/stats` | Platform-wide statistics (rides/day, revenue, active drivers, zone demand). |
| GET | `/api/v1/admin/zones` | Manage zones/carrefours reference data (proxies to Django). |

---

## Cross-Service Call Summary

- **Spring Boot → Django**: `POST /api/v1/geo/verify-destination` during matching, and optionally `/api/v1/optimize/turn` if surfacing suggested turns to drivers through the reservation service.
- **Spring Boot → Node**: `/api/v1/payments/*` when arrival is validated.
- **Frontend → all three**: directly for reads that don't need orchestration (e.g. zones, geocoding), but reservation writes always go through Spring Boot.
- **Any service → Node `/api/v1/email/send`**: for transactional email needs.

Keep this table updated as endpoints are added — it's the contract the whole team builds against.
