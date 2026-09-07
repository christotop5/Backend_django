"""Load VORA Cameroon test seed data into PostgreSQL."""

import json
from pathlib import Path

from django.contrib.auth.hashers import make_password
from django.contrib.gis.geos import LineString, Point
from django.db import transaction
from django.utils import timezone

from accounts.models import Role, User, UserProfile
from config.geo_utils import point_from_latlng
from core.models import Vehicle
from geolocation.models import Carrefour, CorridorLine, DriverLocation, Zone

FIXTURE_PATH = Path(__file__).resolve().parents[2] / 'fixtures' / 'vora_seed.json'
SEED_PASSWORD = 'pass12345'


def _split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(' ', 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], '')


def _ensure_roles() -> dict[str, Role]:
    roles = {}
    for name in ('PASSENGER', 'DRIVER', 'ADMIN'):
        role, _ = Role.objects.get_or_create(name=name, defaults={'permissions': {}})
        roles[name] = role
    return roles


def _load_data() -> dict:
    with FIXTURE_PATH.open(encoding='utf-8') as f:
        return json.load(f)


@transaction.atomic
def run_seed(flush: bool = False) -> dict:
    data = _load_data()
    password_hash = make_password(data.get('password', SEED_PASSWORD))
    roles = _ensure_roles()
    stats = {'zones': 0, 'carrefours': 0, 'corridors': 0, 'passengers': 0, 'drivers': 0}

    if flush:
        User.objects.filter(email__endswith='@vora.cm').delete()
        User.objects.filter(email__in=[p['email'] for p in data['passengers']]).delete()
        Carrefour.objects.all().delete()
        CorridorLine.objects.all().delete()
        Zone.objects.filter(city__in=['Yaoundé', 'Douala']).delete()

    zone_map: dict[tuple[str, str], Zone] = {}
    for c in data['carrefours']:
        key = (c['city'], c['zone'])
        if key not in zone_map:
            zone, created = Zone.objects.get_or_create(
                name=c['zone'],
                city=c['city'],
                defaults={'description': f"Zone {c['zone']} — {c['city']}", 'is_active': True},
            )
            zone_map[key] = zone
            if created:
                stats['zones'] += 1

    for c in data['carrefours']:
        zone = zone_map[(c['city'], c['zone'])]
        _, created = Carrefour.objects.update_or_create(
            id=c['id'],
            defaults={
                'zone': zone,
                'name': c['name'],
                'city': c['city'],
                'location': point_from_latlng(c['lat'], c['lng']),
                'is_pickup_point': True,
                'is_major_intersection': c['is_major_intersection'],
                'typical_waiting_passengers': c['typical_waiting_passengers'],
                'standard_fare_to_centre_fcfa': c['standard_fare_to_centre_fcfa'],
            },
        )
        if created:
            stats['carrefours'] += 1

    for cor in data['corridors']:
        _, created = CorridorLine.objects.update_or_create(
            external_id=cor['id'],
            defaults={
                'code': cor['code'],
                'city': cor['city'],
                'name': cor['name'],
                'start_point': cor['start_point'],
                'end_point': cor['end_point'],
                'stops': cor['stops'],
                'standard_fare_fcfa': cor['standard_fare_fcfa'],
                'distance_km': cor['distance_km'],
                'estimated_duration_min': cor['estimated_duration_min'],
            },
        )
        if created:
            stats['corridors'] += 1

    for p in data['passengers']:
        first, last = _split_name(p['full_name'])
        user, created = User.objects.update_or_create(
            email=p['email'].lower(),
            defaults={
                'role': roles['PASSENGER'],
                'first_name': first,
                'last_name': last,
                'phone': p['phone'],
                'password_hash': password_hash,
                'is_active': True,
                'is_email_verified': p['is_verified'],
            },
        )
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'username': p['username'],
                'city': p['city'],
                'preferred_payment': p['preferred_payment'],
                'rating': p['rating'],
                'total_rides': p['rides_count'],
                'wallet_balance_fcfa': 5000,
            },
        )
        if created:
            stats['passengers'] += 1

    for d in data['taximen']:
        first, last = _split_name(d['full_name'])
        user, created = User.objects.update_or_create(
            email=d['email'].lower(),
            defaults={
                'role': roles['DRIVER'],
                'first_name': first,
                'last_name': last,
                'phone': d['phone'],
                'password_hash': password_hash,
                'is_active': True,
                'is_email_verified': d['is_verified'],
            },
        )
        occupied = d['total_seats'] - d['available_seats']
        cabin = [
            {'seat_id': i, 'seat_name': n, 'is_occupied': i <= occupied}
            for i, n in enumerate(
                ['Avant Passager', 'Arrière Gauche', 'Arrière Droit', 'Arrière Centre'], 1,
            )
        ]
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'username': d['username'],
                'city': d['city'],
                'corridor_axis': d['corridor_line'],
                'active_corridor': d['corridor_line'],
                'rating': d['rating'],
                'total_rides': d['total_trips'],
                'wallet_balance_fcfa': d['daily_revenue_fcfa'],
                'is_online': d['status'] == 'ONLINE',
                'current_lat': d['coordinates']['lat'],
                'current_lng': d['coordinates']['lng'],
                'cabin_seats': cabin,
                'driver_metadata': {
                    'door_number': d['door_number'],
                    'car_year': d['car_year'],
                    'car_color': d['car_color'],
                    'momo_payout_phone': d['momo_payout_phone'],
                    'status': d['status'],
                    'available_seats': d['available_seats'],
                    'total_seats': d['total_seats'],
                    'daily_revenue_fcfa': d['daily_revenue_fcfa'],
                },
            },
        )
        Vehicle.objects.update_or_create(
            registration_number=d['license_plate'].upper(),
            defaults={
                'model': d['car_model'],
                'capacity_kg': 400,
                'status': 'IN_TRANSIT' if d['status'] == 'BUSY' else 'AVAILABLE',
                'assigned_driver': user,
            },
        )
        from geolocation.models import DriverTrajectory

        coords = d['coordinates']
        DriverTrajectory.objects.update_or_create(
            driver=user,
            name=d['corridor_line'],
            defaults={
                'geometry': LineString(
                    (coords['lng'] - 0.01, coords['lat'] - 0.01),
                    (coords['lng'] + 0.01, coords['lat'] + 0.01),
                    srid=4326,
                ),
                'is_active': True,
            },
        )
        latest = DriverLocation.objects.filter(driver=user).order_by('-recorded_at').first()
        point = Point(coords['lng'], coords['lat'], srid=4326)
        if latest is None:
            DriverLocation.objects.create(
                driver=user,
                location=point,
                recorded_at=timezone.now(),
            )
        else:
            latest.location = point
            latest.recorded_at = timezone.now()
            latest.save(update_fields=['location', 'recorded_at'])
        if created:
            stats['drivers'] += 1

    stats['password'] = data.get('password', SEED_PASSWORD)
    return stats
