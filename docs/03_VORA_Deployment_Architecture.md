# VORA — Deployment Architecture

## 1. Overview

VORA is deployed as independent, loosely-coupled services communicating over REST + WebSocket, so each sub-team can build, deploy, and iterate without blocking the others.

```
                        ┌─────────────────────────┐
                        │   React PWA Frontend     │
                        │   (Vercel)               │
                        └────────────┬─────────────┘
                                     │ HTTPS / WSS
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
┌───────────────────┐    ┌────────────────────────┐   ┌────────────────────┐
│  Node.js Service    │    │ Spring Boot Service     │   │ Django Service       │
│  Auth + Payment     │    │ Reservation/Booking     │   │ Geo + Optimization   │
│  (Render)           │◄──►│ (Render, Docker)        │◄─►│ (Render)             │
└───────────────────┘    └────────────┬────────────┘   └──────────┬──────────┘
                                       │                            │
                                       ▼                            ▼
                              ┌─────────────────┐         ┌─────────────────────┐
                              │ PostgreSQL        │         │ PostgreSQL + PostGIS │
                              │ (Reservations DB) │         │ (Geo/Trajectory DB)  │
                              │ Render            │         │ Render               │
                              └─────────────────┘         └─────────────────────┘
                                                                     │
                                                                     ▼
                                                            ┌─────────────────┐
                                                            │ Google Maps APIs  │
                                                            │ (external)        │
                                                            └─────────────────┘
```

Admin Dashboard can be a thin frontend (or a route within the same PWA) reading from all three backends via their `/admin/*` or aggregation endpoints.

## 2. Service-by-Service Stack

### 2.1 Frontend — React PWA
- **Stack**: React JS, service worker for PWA/offline shell, Google Maps JS SDK (or Mapbox GL) for map rendering.
- **Host**: Vercel.
- **Env vars**: `VITE_API_AUTH_URL`, `VITE_API_RESERVATION_URL`, `VITE_API_GEO_URL`, `VITE_GOOGLE_MAPS_API_KEY`, `VITE_WS_URL`.
- **Build**: standard Vercel auto-deploy from the `main`/`develop` branch; preview deployments on PRs are useful for design review during the hackathon.

### 2.2 Node.js Service — Auth & Payment
- **Stack**: Node.js (Express or NestJS), JWT issuance, Google OAuth client, Orange Money & MTN MoMo SDK/API integration.
- **Host**: Render (Web Service).
- **Env vars**: `JWT_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ORANGE_MONEY_API_KEY`, `MTN_MOMO_API_KEY`, `EMAIL_API_KEY`, `DATABASE_URL` (if it owns a users table) or shared auth DB.
- **Notes**: keep this service stateless where possible (JWT-based) so it can scale independently; webhooks from payment providers must hit public HTTPS endpoints — Render's default URL works for the hackathon.

### 2.3 Spring Boot Service — Reservation/Booking
- **Stack**: Spring Boot 3.x, Java 17+, Spring Data JPA, Spring Security (JWT validation), WebSocket/STOMP, PostgreSQL.
- **Host**: Render (Docker-based Web Service — Spring Boot deploys cleanly as a container).
- **Dockerfile**: multi-stage build (Maven/Gradle build stage → slim JRE runtime stage) to keep the image small and cold-starts fast on Render's free/hobby tier.
- **Env vars**: `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`, `JWT_PUBLIC_KEY` (or shared secret with Node), `DJANGO_GEO_SERVICE_URL`, `NODE_PAYMENT_SERVICE_URL`, `FCM_SERVER_KEY`.
- **Real-time**: expose a WebSocket endpoint (`/ws`) with STOMP over it; Render supports long-lived connections on Web Services, confirm sticky sessions aren't required (STOMP here is stateless per-connection, should be fine on a single instance for the hackathon).

### 2.4 Django Service — Geolocation & Optimization
- **Stack**: Django + Django REST Framework, GeoDjango, PostgreSQL + PostGIS extension, Google Maps Platform (Geocoding, Directions).
- **Host**: Render (Web Service) — both API and its PostGIS-enabled Postgres instance on Render.
- **Env vars**: `DATABASE_URL` (PostGIS-enabled), `GOOGLE_MAPS_API_KEY`, `TRAJECTORY_TOLERANCE_METERS`, `SPRING_BOOT_RESERVATION_SERVICE_URL` (for the internal pending-reservations lookup described in the optimization doc).
- **Notes**: Render's managed Postgres supports enabling the PostGIS extension — confirm this is done at DB creation (`CREATE EXTENSION postgis;`) before running Django migrations that use geometry fields.

## 3. Inter-Service Communication

| Caller | Callee | Protocol | Purpose |
|---|---|---|---|
| Frontend | Node | HTTPS | Auth, payment initiation |
| Frontend | Spring Boot | HTTPS + WSS | Reservations, live tracking |
| Frontend | Django | HTTPS | Zones, geocoding reads |
| Spring Boot | Django | HTTPS (internal) | `verify-destination`, `optimize/turn` |
| Spring Boot | Node | HTTPS (internal) | Trigger payment on arrival |
| Django | Spring Boot | HTTPS (internal) | Read pending reservations for optimization |
| Any service | Node `/email/send` | HTTPS (internal) | Transactional email |

Use a shared **JWT secret/public key** across services so Spring Boot and Django can independently validate tokens issued by Node without calling it on every request.

## 4. Environment & Secrets Management

- Every service ships a `.env.example` (never real secrets) per the hackathon's documentation requirement.
- Set real secrets directly in each Render service's **Environment** tab (and Vercel's **Environment Variables** for the frontend) — never commit them to GitHub.
- Recommended shared secrets to keep consistent across services: `JWT_SECRET` (or public key), `TRAJECTORY_TOLERANCE_METERS`.

## 5. CI/CD for the Hackathon

- **Frontend**: Vercel auto-deploys every push to `main`; PR previews for `feature/*` branches.
- **Backends on Render**: enable auto-deploy from `main` for each service's Render app; keep `develop` as the integration branch and merge to `main` only when a service is demo-ready, to avoid breaking the live demo mid-hackathon.
- Branch naming per the hackathon manual: `feature/authentication`, `feature/map`, `feature/booking`, `feature/driver`, `feature/security`, `feature/ai`, `feature/optimization`.

## 6. Deployment Checklist (per service)

- [ ] Dockerfile builds and runs locally (Spring Boot).
- [ ] `.env.example` committed, real `.env` gitignored.
- [ ] PostGIS extension enabled before Django migrations run.
- [ ] CORS configured on Node, Spring Boot, and Django to allow the Vercel frontend origin.
- [ ] Health-check endpoint (`/health` or `/actuator/health`) on every backend service for Render's health checks.
- [ ] WebSocket endpoint reachable over `wss://` from the deployed frontend (test after Render assigns the HTTPS URL).
- [ ] Shared JWT secret confirmed identical across Node/Spring Boot/Django.

## 7. Demo-Day Notes

- Render free/hobby services can cold-start after inactivity — do a warm-up call to each service a few minutes before the live demo.
- Keep a fallback: if Google Maps API quota or a payment provider sandbox misbehaves during the demo, have a short recorded backup clip of that flow, as the manual explicitly allows simulated payments.
