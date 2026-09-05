"""PostGIS corridor matching against driver trajectories."""

from django.contrib.gis.geos import Point

from geolocation.models import DriverTrajectory
from optimization.models import DemandCache


def get_active_trajectory(driver_id: int) -> DriverTrajectory | None:
    return (
        DriverTrajectory.objects
        .filter(driver_id=driver_id, is_active=True)
        .order_by('-updated_at')
        .first()
    )


def destination_within_corridor(
    driver_id: int,
    destination: Point,
    tolerance_meters: int | None = None,
) -> dict:
    trajectory = get_active_trajectory(driver_id)
    if trajectory is None:
        return {
            'verified': False,
            'driver_id': driver_id,
            'reason': 'no_active_trajectory',
            'distance_meters': None,
            'tolerance_meters': tolerance_meters,
        }

    tol = tolerance_meters or trajectory.tolerance_meters
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT ST_Distance(
                %s::geography,
                ST_GeomFromText(%s, 4326)::geography
            )
            ''',
            [destination.ewkt, trajectory.geometry.wkt],
        )
        dist_m = cursor.fetchone()[0]

    return {
        'verified': dist_m <= tol,
        'driver_id': driver_id,
        'trajectory_id': trajectory.id,
        'distance_meters': round(dist_m, 2),
        'tolerance_meters': tol,
    }


def demand_in_corridor(driver_id: int) -> list[DemandCache]:
    trajectory = get_active_trajectory(driver_id)
    if trajectory is None:
        return []

    tol = trajectory.tolerance_meters
    return list(
        DemandCache.objects.extra(
            where=[
                'ST_DWithin('
                '  destination_location::geography, '
                '  ST_GeomFromText(%s, 4326)::geography, '
                '  %s'
                ')',
            ],
            params=[trajectory.geometry.wkt, tol],
        ).order_by('-proposed_price')
    )


def demand_in_zone(zone_id: int) -> list[DemandCache]:
    from geolocation.models import Zone

    zone = Zone.objects.filter(pk=zone_id, is_active=True).first()
    if zone is None or zone.boundary is None:
        return list(DemandCache.objects.all())

    return list(
        DemandCache.objects.filter(
            pickup_location__within=zone.boundary,
        )
    )
