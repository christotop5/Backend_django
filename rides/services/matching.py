"""Match passengers to nearest available online drivers."""

from accounts.models import Role, User, UserProfile
from core.models import Vehicle
from rides.services.geo import carrefour_latlng, haversine_km


def _driver_free_seats(profile: UserProfile) -> int:
    meta = profile.driver_metadata or {}
    if 'available_seats' in meta:
        return int(meta['available_seats'])
    seats = profile.cabin_seats or []
    if seats:
        return sum(1 for s in seats if not s.get('is_occupied'))
    return 4


def _driver_location(profile: UserProfile) -> tuple[float, float] | None:
    if profile.current_lat is not None and profile.current_lng is not None:
        return float(profile.current_lat), float(profile.current_lng)
    return None


def find_nearby_drivers(
    lat: float,
    lng: float,
    seats_needed: int = 1,
    city: str | None = None,
    limit: int = 10,
) -> list[dict]:
    driver_role = Role.objects.filter(name='DRIVER').first()
    if not driver_role:
        return []

    qs = User.objects.filter(
        role=driver_role,
        is_active=True,
        profile__is_online=True,
    ).select_related('profile')
    if city:
        qs = qs.filter(profile__city__icontains=city)

    candidates = []
    for driver in qs:
        profile = driver.profile
        free = _driver_free_seats(profile)
        if free < seats_needed:
            continue
        loc = _driver_location(profile)
        if loc is None:
            continue
        dist_km = haversine_km(lat, lng, loc[0], loc[1])
        vehicle = Vehicle.objects.filter(assigned_driver=driver).first()
        meta = profile.driver_metadata or {}
        candidates.append({
            'driver_id': driver.id,
            'driver_public_id': f'usr_{driver.id}',
            'full_name': f'{driver.first_name} {driver.last_name}'.strip(),
            'phone': driver.phone,
            'rating': float(profile.rating),
            'license_plate': vehicle.registration_number if vehicle else None,
            'car_model': vehicle.model if vehicle else None,
            'corridor_line': profile.corridor_axis,
            'available_seats': free,
            'total_seats': meta.get('total_seats', 4),
            'location': {'lat': loc[0], 'lng': loc[1]},
            'distance_km': round(dist_km, 2),
            'eta_seconds': max(int(dist_km * 360), 60),
        })

    candidates.sort(key=lambda d: d['distance_km'])
    return candidates[:limit]


def match_driver_for_ride(pickup_carrefour_id: int, seats_needed: int, city: str | None = None) -> User | None:
    pickup = carrefour_latlng(pickup_carrefour_id)
    if pickup is None:
        return None
    nearby = find_nearby_drivers(
        pickup['lat'], pickup['lng'],
        seats_needed=seats_needed,
        city=city,
        limit=1,
    )
    if not nearby:
        return None
    return User.objects.filter(pk=nearby[0]['driver_id']).first()


def serialize_driver_for_ride(driver: User) -> dict:
    profile = driver.profile
    vehicle = Vehicle.objects.filter(assigned_driver=driver).first()
    meta = profile.driver_metadata or {}
    loc = _driver_location(profile)
    free = _driver_free_seats(profile)
    return {
        'id': f'usr_{driver.id}',
        'driver_id': driver.id,
        'name': f'{driver.first_name} {driver.last_name}'.strip(),
        'phone': driver.phone or '',
        'vehicle_plate': vehicle.registration_number if vehicle else None,
        'car_model': vehicle.model if vehicle else None,
        'rating': float(profile.rating),
        'corridor_line': profile.corridor_axis,
        'available_seats': free,
        'total_seats': meta.get('total_seats', 4),
        'occupied_seats': meta.get('total_seats', 4) - free,
        'current_lat': loc[0] if loc else None,
        'current_lng': loc[1] if loc else None,
        'location': {'lat': loc[0], 'lng': loc[1]} if loc else None,
    }
