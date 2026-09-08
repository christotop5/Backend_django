# VORA — Map & Ride Lifecycle (Frontend Guide)

Base URL: `https://vora-ujbv.onrender.com/api/v1`

---

## Ride flow (status machine)

```
pending_approval  →  driver POST /driver/rides/{id}/approve
       ↓
approved          →  passenger POST /rides/{id}/passenger-arrived  ("I'm here")
       ↓
passenger_arrived →  passenger POST /rides/{id}/board  ("I'm in the car")
       ↓
in_trip           →  driver POST /driver/rides/{id}/complete
       ↓
awaiting_payment  →  passenger POST /rides/{id}/payment  (credentials asked HERE only)
       ↓
(rate)            →  passenger POST /rides/{id}/rate  → completed
```

**Payment is only at trip end** — `payment_method` on request is a preference; MoMo phone is sent with `/payment`.

---

## Radar & map (before booking)

### Nearest carrefours (passenger GPS)
```http
GET /geo/nearest-carrefour?lat=3.8744&lng=11.4988&limit=5&city=Yaoundé
```

### Nearby taxis on map (real drivers, not fake)
```http
GET /rides/nearby-drivers?lat=3.8744&lng=11.4988&seats=1&city=Yaoundé
```

Response includes `recommended_driver` (closest with free seats).

---

## Book ride (real driver match)

```http
POST /rides/request
Authorization: Bearer <passenger_token>

{
  "pickup_carrefour_id": 4,
  "pickup_name": "Marché Mokolo",
  "destination_carrefour_id": 2,
  "destination_name": "Rond-point Bastos",
  "ride_type": "shared",
  "seats_count": 2,
  "payment_method": "momo",
  "passenger_lat": 3.8744,
  "passenger_lng": 11.4988
}
```

- Assigns **nearest online driver** with enough seats  
- Status: `pending_approval`  
- **No payment yet**

---

## Passenger map (poll every 5–10s)

```http
GET /rides/{ride_id}/map
GET /rides/{ride_id}/status
```

Returns:
- `driver.location` — taxi position on map  
- `pickup.location` / `destination.location` — carrefour markers  
- `status`, `payment_status`, `timeline`

---

## Driver map

```http
GET /driver/rides/pending      # approve/reject list
GET /driver/rides/active       # passengers to show on map
GET /driver/rides/{ride_id}/map
```

Each active ride includes `passenger_pickup_marker` with passenger info + pickup GPS.

---

## Driver actions

| Action | Endpoint |
|--------|----------|
| Accept | `POST /driver/rides/{id}/approve` |
| Reject | `POST /driver/rides/{id}/reject` |
| End trip | `POST /driver/rides/{id}/complete` |

---

## Passenger actions

| Action | Endpoint |
|--------|----------|
| I'm at pickup | `POST /rides/{id}/passenger-arrived` |
| I'm in the car | `POST /rides/{id}/board` — occupies `seats_count` in driver cabin |
| Pay | `POST /rides/{id}/payment` `{ "phone_number": "+237...", "payment_method": "momo" }` |
| Rate | `POST /rides/{id}/rate` |

---

## Map UI checklist

**Passenger screen**
1. Show user GPS + `GET /geo/nearest-carrefour` radar pins  
2. Show `GET /rides/nearby-drivers` as taxi markers  
3. After book → poll `/rides/{id}/map` until `approved`  
4. After board → follow driver marker until `awaiting_payment`  
5. Show payment form only when `status === awaiting_payment`

**Driver screen**
1. Poll `GET /driver/rides/pending` for notifications  
2. On accept → show passenger pickup on map (`passenger_pickup_marker`)  
3. After board → navigation to destination carrefour  
4. Complete → wait for passenger payment

---

## Status values

| status | Meaning |
|--------|---------|
| `pending_approval` | Waiting driver |
| `approved` | Driver accepted — passenger can come |
| `passenger_arrived` | Passenger at pickup |
| `in_trip` | Passenger onboard, seats occupied |
| `awaiting_payment` | Trip done — pay now |
| `completed` | Paid & rated |
| `rejected` | Driver declined |
