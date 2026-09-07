"""OpenAPI / Swagger metadata for the VORA platform."""

OPENAPI_DESCRIPTION = """
# VORA — Plateforme Taxi Jaune (Cameroun)

API REST unifiée pour l'écosystème **VORA** : application passager, cockpit chauffeur (taxi jaune),
géolocalisation PostGIS, optimisation de tournées, paiements Mobile Money simulés et administration.

**Production :** `https://vora-ujbv.onrender.com/api/v1`  
**Documentation interactive :** `/api/v1/docs/`  
**Schéma OpenAPI :** `/api/v1/schema/`

---

## Architecture système

| Couche | Rôle |
|--------|------|
| **Frontend** (mobile / web) | UI passager & chauffeur — consomme cette API |
| **Django (ce service)** | Auth JWT, courses, paiements simulés, zones/carrefours, trajectoires, optimisation PostGIS |
| **PostgreSQL + PostGIS** | Données géo (zones, carrefours, corridors, positions chauffeurs) |
| **Google Maps API** | Géocodage, itinéraires, congestion |
| **Spring Boot** *(optionnel)* | Réservations — appelle `verify-destination` et `optimize/turn` |

---

## Rôles utilisateur

| Rôle | `role` JWT | Espace frontend | Endpoints principaux |
|------|------------|-----------------|----------------------|
| **Passager** | `passenger` | `pickup` — commander une course | `/rides/*`, `/payments/*`, `/safety/sos` |
| **Chauffeur** | `driver` | `driver-cockpit` — habitacle & revenus | `/driver/*`, `/drivers/online` (lecture) |
| **Admin** | `admin` *(futur)* | Dashboard ops | `/admin/*` |

Après connexion, utiliser `user.redirect_dashboard` : `pickup` ou `driver-cockpit`.

---

## Authentification

1. **Inscription** — `POST /auth/signup` (`role`: `passenger` \| `driver`)
2. **OTP** — `POST /auth/otp/verify` avec code **`1234`** (simulation)
3. **Connexion** — `POST /auth/signin` → `access_token` (24 h) + `refresh_token` (7 j)
4. **Renouvellement** — `POST /auth/refresh` → nouveaux tokens (rotation — remplacer les deux)
5. **Déconnexion** — `POST /auth/logout` → révoque le refresh token
6. **Requêtes protégées** — header `Authorization: Bearer <access_token>`
7. **Profil** — `GET /auth/me`

Guide frontend détaillé : `docs/FRONTEND_AUTH.md`

Cliquez **Authorize** en haut à droite et entrez : `Bearer eyJ...`

---

## Données de test (seed)

Commande : `python manage.py seed_vora`

| Entité | Quantité | Villes |
|--------|----------|--------|
| Passagers | 50 | Yaoundé & Douala |
| Chauffeurs (taximen jaunes) | 10 | Yaoundé & Douala |
| Carrefours | 32 | GPS réels |
| Lignes / corridors | 6 | Y1–Y3, D1–D3 |

**Mot de passe (tous les comptes seed) :** `pass12345`

| Rôle | Email exemple |
|------|---------------|
| Passager | `marie.ebanda@gmail.com` |
| Chauffeur | `alain.mvondo@vora.cm` |

---

## Parcours passager (flow)

```
GET /carrefours?city=Yaoundé
    ↓
POST /rides/estimate  { pickup_carrefour_id, destination_carrefour_id, ride_type }
    ↓
POST /rides/request   { payment_method: cash|momo|om|wallet }
    ↓
GET  /rides/{ride_id}/status   (polling statut + chauffeur simulé)
    ↓
POST /rides/{ride_id}/payment  (si paiement à l'arrivée)
    ↓
POST /rides/{ride_id}/rate     (note + pourboire simulé)
```

---

## Parcours chauffeur (flow)

```
POST /driver/status      { is_online, current_location }
    ↓
POST /driver/corridor    { corridor_id: "Y1", direction: aller|retour }
    ↓
PATCH /driver/cabin-seats/{seat_id}   (occupation sièges, tarif rotation)
    ↓
POST /driver/withdraw    (retrait Mobile Money simulé)
```

Corridor IDs : `Y1`, `Y2`, `Y3` (Yaoundé), `D1`, `D2`, `D3` (Douala) — voir `GET /corridors`.

---

## Paiements (simulation)

> **Aucun FCFA réel n'est débité.** Toutes les réponses incluent `"simulation": true`.

| Méthode | Endpoint |
|---------|----------|
| MTN MoMo | `POST /payments/mtn-momo` |
| Orange Money | `POST /payments/orange-money` |
| Espèces | `POST /payments/cash/confirm` |
| Statut | `GET /payments/{transaction_id}/status` |

---

## Géolocalisation & optimisation

| Endpoint | Usage |
|----------|-------|
| `GET /geo/geocode` | Adresse → coordonnées |
| `GET /geo/route` | Itinéraire Google Maps |
| `GET /zones`, `/carrefours`, `/corridors` | Données de référence |
| `GET /drivers/online` | Chauffeurs disponibles (public) |
| `POST /geo/verify-destination` | Vérifier si destination ∈ corridor chauffeur (PostGIS) |
| `POST /optimize/turn` | Optimisation greedy tournée (jusqu'à 4 passagers) |

---

## Format des réponses

Succès :
```json
{ "success": true, "message": "...", "data": { ... } }
```

Erreur :
```json
{
  "success": false,
  "error": { "code": "INVALID_CREDENTIALS", "message": "..." },
  "timestamp": "2026-09-07T00:00:00Z"
}
```

---

## Codes d'erreur courants

| Code | HTTP | Signification |
|------|------|---------------|
| `INVALID_CREDENTIALS` | 401 | Email ou mot de passe incorrect |
| `ACCOUNT_NOT_VERIFIED` | 403 | OTP non validé |
| `VALIDATION_FAILED` | 400 | Champs invalides |
| `RIDE_CONFLICT` | 409 | Course déjà en cours |
| `INSUFFICIENT_FUNDS` | 402 | Solde portefeuille insuffisant |
| `NOT_FOUND` | 404 | Ressource introuvable |
"""

OPENAPI_TAGS = [
    {
        'name': 'System',
        'description': 'Santé du service et métadonnées de déploiement.',
    },
    {
        'name': 'Auth',
        'description': (
            'Inscription, vérification OTP (code fixe **1234** en simulation), '
            'connexion JWT et profil utilisateur. '
            'Deux rôles : `passenger` et `driver`.'
        ),
    },
    {
        'name': 'Rides',
        'description': (
            'Parcours **passager** : estimation tarif, demande de course, suivi statut, '
            'paiement à l\'arrivée et notation. Nécessite JWT rôle passager côté frontend.'
        ),
    },
    {
        'name': 'Driver',
        'description': (
            'Parcours **chauffeur taxi jaune** : mise en ligne, sélection de corridor, '
            'gestion des 4 sièges habitacle, retrait Mobile Money simulé. '
            '`GET /drivers/online` est public (liste des chauffeurs en ligne).'
        ),
    },
    {
        'name': 'Payments',
        'description': (
            'MTN MoMo, Orange Money et espèces — **simulation uniquement**, '
            'aucun argent réel. Webhooks simulés pour tests d\'intégration.'
        ),
    },
    {
        'name': 'Safety',
        'description': 'Alerte SOS avec position GPS — enregistrement signalement + notification simulée.',
    },
    {
        'name': 'Geolocation',
        'description': 'Wrapper Google Maps : géocodage, géocodage inverse, itinéraires et congestion par zone.',
    },
    {
        'name': 'Zones',
        'description': 'Zones urbaines taxi (Yaoundé & Douala) avec limites PostGIS optionnelles.',
    },
    {
        'name': 'Carrefours',
        'description': (
            '32 carrefours seedés (Yaoundé & Douala) : coordonnées GPS, zone, '
            'passagers en attente typiques, tarif standard vers le centre.'
        ),
    },
    {
        'name': 'Corridors',
        'description': (
            '6 lignes urbaines taxi jaune (Y1–Y3 Yaoundé, D1–D3 Douala) : '
            'arrêts, tarif standard, distance et durée estimée.'
        ),
    },
    {
        'name': 'Driver Trajectories',
        'description': (
            'Corridors de travail déclarés par chauffeur (LineString PostGIS). '
            'Utilisés par l\'optimiseur et `verify-destination`.'
        ),
    },
    {
        'name': 'Optimization',
        'description': (
            'Moteur d\'optimisation MVP : matching PostGIS ST_DWithin, '
            'sélection greedy jusqu\'à 4 passagers, heatmap demande.'
        ),
    },
    {
        'name': 'Admin',
        'description': 'Agrégations dashboard : zones, signalements, statistiques journalières.',
    },
]

OPENAPI_SERVERS = [
    {'url': 'https://vora-ujbv.onrender.com/api/v1', 'description': 'Production (Render — Frankfurt)'},
    {'url': 'http://localhost:8000/api/v1', 'description': 'Développement local'},
]

OPENAPI_EXTERNAL_DOCS = {
    'url': 'https://github.com/vora-cm/backend/blob/main/Backend_django/docs/API.md',
    'description': 'Guide API complet (Markdown)',
}
