"""Greedy turn optimizer — MVP cheapest-insertion fallback."""

from __future__ import annotations

from django.utils import timezone

from config.geo_utils import latlng_from_point
from optimization.models import DemandCache, OptimizationRun
from optimization.services.corridor import demand_in_corridor, get_active_trajectory

MAX_PASSENGERS = 4


def _build_stop(demand: DemandCache, stop_type: str) -> dict:
    point = demand.pickup_location if stop_type == 'pickup' else demand.destination_location
    return {
        'type': stop_type,
        'reservation_id': demand.reservation_id,
        'location': latlng_from_point(point),
        'proposed_price': float(demand.proposed_price),
    }


def optimize_turn(driver_id: int, zone_id: int | None = None) -> dict:
    """
    MVP algorithm (doc §8):
    1. Filter candidates by corridor (PostGIS ST_DWithin)
    2. Sort by proposed_price descending
    3. Greedily fill up to 4 seats
    """
    trajectory = get_active_trajectory(driver_id)
    if trajectory is None:
        return {
            'driver_id': driver_id,
            'turn': [],
            'expected_revenue': 0,
            'expected_duration_minutes': 0,
            'message': 'No active trajectory for driver',
        }

    candidates = demand_in_corridor(driver_id)
    if zone_id is not None:
        from optimization.services.corridor import demand_in_zone
        zone_ids = {d.reservation_id for d in demand_in_zone(zone_id)}
        candidates = [c for c in candidates if c.reservation_id in zone_ids]

    selected = candidates[:MAX_PASSENGERS]
    turn: list[dict] = []
    for demand in selected:
        turn.append(_build_stop(demand, 'pickup'))
    for demand in selected:
        turn.append(_build_stop(demand, 'dropoff'))

    expected_revenue = sum(float(d.proposed_price) for d in selected)
    expected_duration = len(selected) * 10  # heuristic minutes per leg

    output = {
        'driver_id': driver_id,
        'trajectory_id': trajectory.id,
        'turn': turn,
        'expected_revenue': expected_revenue,
        'expected_duration_minutes': expected_duration,
        'candidate_count': len(candidates),
        'selected_count': len(selected),
    }

    OptimizationRun.objects.create(
        driver_id=driver_id,
        input_snapshot={
            'zone_id': zone_id,
            'candidates': [c.reservation_id for c in candidates],
        },
        output_turn=output,
        expected_revenue=expected_revenue,
    )
    return output
