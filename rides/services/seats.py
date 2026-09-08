"""Driver cabin seat occupation tied to rides."""

from accounts.models import UserProfile
from rides.models import Ride

DEFAULT_SEATS = [
    {'seat_id': 1, 'seat_name': 'Avant Passager', 'is_occupied': False},
    {'seat_id': 2, 'seat_name': 'Arrière Gauche', 'is_occupied': False},
    {'seat_id': 3, 'seat_name': 'Arrière Droit', 'is_occupied': False},
    {'seat_id': 4, 'seat_name': 'Arrière Centre', 'is_occupied': False},
]


def _ensure_seats(profile: UserProfile) -> list:
    if not profile.cabin_seats:
        profile.cabin_seats = [s.copy() for s in DEFAULT_SEATS]
        profile.save(update_fields=['cabin_seats'])
    return profile.cabin_seats


def _sync_metadata_seats(profile: UserProfile, seats: list) -> None:
    meta = dict(profile.driver_metadata or {})
    free = sum(1 for s in seats if not s.get('is_occupied'))
    meta['available_seats'] = free
    meta['total_seats'] = len(seats) or 4
    profile.driver_metadata = meta


def occupy_seats_for_ride(driver_profile: UserProfile, ride: Ride) -> list[int]:
    seats = _ensure_seats(driver_profile)
    needed = ride.seats_count
    occupied_ids = []
    for seat in seats:
        if needed <= 0:
            break
        if not seat.get('is_occupied'):
            seat['is_occupied'] = True
            seat['ride_id'] = ride.ride_id
            seat['passenger_type'] = 'vora_app'
            seat['pickup_point'] = ride.pickup_name
            seat['dropoff_point'] = ride.destination_name
            seat['fare_fcfa'] = ride.fare_fcfa
            seat['payment_status'] = 'pending'
            occupied_ids.append(seat['seat_id'])
            needed -= 1
    if not occupied_ids:
        raise ValueError('Pas assez de sièges libres dans ce taxi.')
    driver_profile.cabin_seats = seats
    _sync_metadata_seats(driver_profile, seats)
    driver_profile.save(update_fields=['cabin_seats', 'driver_metadata'])
    ride.metadata = {**ride.metadata, 'occupied_seat_ids': occupied_ids}
    ride.save(update_fields=['metadata'])
    return occupied_ids


def release_seats_for_ride(driver_profile: UserProfile, ride: Ride) -> None:
    seats = _ensure_seats(driver_profile)
    seat_ids = ride.metadata.get('occupied_seat_ids', [])
    for seat in seats:
        if seat.get('ride_id') == ride.ride_id or seat.get('seat_id') in seat_ids:
            seat['is_occupied'] = False
            seat.pop('ride_id', None)
            seat.pop('passenger_type', None)
            seat.pop('pickup_point', None)
            seat.pop('dropoff_point', None)
            seat.pop('fare_fcfa', None)
            seat.pop('payment_status', None)
    driver_profile.cabin_seats = seats
    _sync_metadata_seats(driver_profile, seats)
    driver_profile.save(update_fields=['cabin_seats', 'driver_metadata'])
