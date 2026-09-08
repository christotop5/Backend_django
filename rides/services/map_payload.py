"""Map payload builders for passenger and driver UIs."""

from rides.models import Ride
from rides.services.geo import carrefour_latlng
from rides.services.matching import serialize_driver_for_ride


def build_ride_map_payload(ride: Ride, viewer: str = 'passenger') -> dict:
    pickup = carrefour_latlng(ride.pickup_carrefour_id)
    destination = carrefour_latlng(ride.destination_carrefour_id)
    driver = None
    if ride.driver_id:
        driver = serialize_driver_for_ride(ride.driver)

    passenger = {
        'id': f'usr_{ride.passenger_id}',
        'name': f'{ride.passenger.first_name} {ride.passenger.last_name}'.strip(),
        'phone': ride.passenger.phone or '',
        'seats_count': ride.seats_count,
    }

    payload = {
        'ride_id': ride.ride_id,
        'status': ride.status,
        'payment_method': ride.payment_method,
        'payment_status': ride.metadata.get('payment_status', 'pending'),
        'fare_fcfa': ride.fare_fcfa,
        'pickup': {
            'carrefour_id': ride.pickup_carrefour_id,
            'name': ride.pickup_name,
            'location': pickup,
        },
        'destination': {
            'carrefour_id': ride.destination_carrefour_id,
            'name': ride.destination_name,
            'location': destination,
        },
        'driver': driver,
        'passenger': passenger,
        'timeline': {
            'requested_at': ride.created_at.isoformat(),
            'driver_approved_at': ride.metadata.get('driver_approved_at'),
            'passenger_arrived_at': ride.metadata.get('passenger_arrived_at'),
            'boarded_at': ride.metadata.get('boarded_at'),
            'trip_ended_at': ride.metadata.get('trip_ended_at'),
            'paid_at': ride.metadata.get('paid_at'),
        },
    }

    if viewer == 'driver' and pickup:
        payload['passenger_pickup_marker'] = {
            **passenger,
            'location': pickup,
            'status': ride.status,
        }
    return payload
