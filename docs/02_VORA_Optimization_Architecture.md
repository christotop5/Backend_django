# VORA — Turn Optimization Architecture (Django Service)

## 1. Purpose

This document defines how the Django service computes an **optimal "turn"** for a driver: the ordered sequence of pickups/drop-offs along a chosen work zone that maximizes the driver's expected revenue for that trip, mirroring how Yaoundé taxi drivers already pick up multiple passengers heading the same general direction and swap passengers at successive carrefours.

This is the single most important piece of "innovation" in VORA's pitch — it must be genuinely explainable to the jury, not a black box.

## 2. Problem Framing

This is a constrained variant of the **Dial-a-Ride Problem (DARP)** / **Vehicle Routing Problem with Pickup and Delivery (VRPPD)**, simplified for the hackathon:

- **Vehicle capacity**: fixed at ~4 passengers (Cameroonian taxi norm — 2 front, 2 back).
- **Objective**: maximize `Σ(proposed_price of matched passengers) − operating_cost(distance, time)` for the turn, not just minimize distance.
- **Constraint**: every passenger's destination must lie on or near (within tolerance) the driver's declared trajectory — we are not asking the driver to detour arbitrarily, only to sequence pickups/drop-offs *within* the corridor they already intend to drive.
- **Real-time**: demand changes continuously; the "optimal turn" is recomputed as new reservation requests appear or seats free up.

Because full DARP solving is NP-hard and 48 hours doesn't allow an exact solver, VORA uses a **greedy heuristic with local re-optimization**, which is standard practice for real-time ride-matching MVPs (this is also defensible to the jury as an intentional, explained trade-off rather than a limitation you're unaware of).

## 3. High-Level Pipeline

```
Driver declares trajectory (LineString of zones/carrefours)
        ↓
PostGIS query: find pending reservations whose
   destination is within tolerance of trajectory
        ↓
Candidate demand points (each with: pickup point,
   destination, proposed price, requested_at)
        ↓
Greedy insertion heuristic (Section 4)
        ↓
Ranked, ordered "turn": [pickup A → pickup B → drop B →
   pickup C → drop A → drop C ...]
        ↓
Turn returned to driver via /api/v1/optimize/turn
        ↓
Re-optimize whenever: driver accepts/rejects a leg,
   a seat frees up, or a new higher-value request
   appears within the corridor
```

## 4. Matching & Sequencing Algorithm

### Step 1 — Corridor filtering (PostGIS)
For a driver's active trajectory (stored as a `LineString`), find all pending reservation destinations within a buffer distance using:

```sql
SELECT * FROM reservations
WHERE ST_DWithin(
  destination_point::geography,
  driver_trajectory::geography,
  :tolerance_meters
)
AND status = 'EN_ATTENTE';
```

`tolerance_meters` is configurable (start at 500m–1km per the Spring Boot spec) and can be tuned per zone (tighter in dense zones, looser in sparse ones).

### Step 2 — Score each candidate passenger

For each candidate `p`, compute a score combining revenue and detour cost:

```
score(p) = proposed_price(p)
           − detour_cost(p)         # extra distance/time vs. direct trajectory
           + urgency_bonus(p)       # small bonus for requests waiting longer
```

`detour_cost` is estimated via the Google Maps Directions API (distance/duration delta between "trajectory as-is" and "trajectory with p's pickup+drop inserted").

### Step 3 — Greedy insertion (cheapest insertion heuristic)

1. Start with the driver's empty turn (just the trajectory itself).
2. Repeatedly insert the highest-scoring remaining candidate at the position in the route that minimizes added detour, as long as:
   - vehicle capacity (4) isn't exceeded at any point along the route, and
   - the candidate's destination stays within tolerance of the original trajectory.
3. Stop when no remaining candidate improves total expected net revenue, or capacity is full.

This is a well-known, explainable approach ("cheapest insertion" / greedy VRP heuristic) — good enough for real-time performance and easy to defend to the jury.

### Step 4 — Output

Return an ordered stop list:

```json
{
  "driver_id": "DRV-00125",
  "turn": [
    { "type": "pickup", "reservation_id": "RES-1", "location": {...} },
    { "type": "pickup", "reservation_id": "RES-2", "location": {...} },
    { "type": "dropoff", "reservation_id": "RES-2", "location": {...} },
    { "type": "pickup", "reservation_id": "RES-3", "location": {...} },
    { "type": "dropoff", "reservation_id": "RES-1", "location": {...} },
    { "type": "dropoff", "reservation_id": "RES-3", "location": {...} }
  ],
  "expected_revenue": 4500,
  "expected_duration_minutes": 38
}
```

## 5. Re-optimization Triggers

Recompute the turn (not necessarily from scratch — incremental insertion is enough) when:
- A new reservation appears inside the driver's active corridor.
- A passenger cancels.
- A leg of the turn is completed (a pickup or drop-off happens) — re-run insertion on remaining candidates.

## 6. Data Needed (owned by Django + PostGIS)

- `DriverTrajectory` (LineString geometry, active flag)
- Live `Reservation` feed (read from Spring Boot's DB or via an internal API call — decide with the team whether Django reads Spring Boot's DB directly or calls an endpoint; **recommendation: call an internal `/api/v1/internal/reservations/pending?zone_id=` endpoint on Spring Boot** rather than sharing a DB, to keep services decoupled)
- Zones / carrefours reference table
- Google Maps Directions API for detour cost estimation

## 7. What to Say to the Jury

- **Problem type**: constrained pickup-and-delivery routing under real-time demand.
- **Why greedy insertion, not an exact solver**: NP-hard problem, needs sub-second response for a live app; greedy insertion is the industry-standard trade-off (used in early-stage ride-pooling systems) and is fully explainable.
- **Why PostGIS**: enables efficient spatial filtering (`ST_DWithin`) instead of computing distance in application code for every candidate — this is the "why this technology" justification the manual asks for.
- **Limits to acknowledge openly**: not globally optimal, tolerance values are heuristic and would need real usage data to tune, and detour cost currently ignores live traffic congestion (a good "next step" to mention).

## 8. MVP Simplification (if time runs out)

If full insertion logic can't be finished in time, a fallback that still demonstrates the concept:
1. Filter candidates by corridor (Step 1) — this alone is a real feature.
2. Sort by `proposed_price` descending.
3. Greedily fill the 4 seats in that order, skipping any that would push a destination outside tolerance.

This is a legitimate, presentable MVP of the same idea, just without full route-order optimization.
