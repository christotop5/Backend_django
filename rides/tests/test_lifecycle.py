"""Ride lifecycle tests with mocked matching."""

import json
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role, User, UserProfile
from accounts.services.jwt_service import create_access_token
from config.geo_utils import point_from_latlng
from core.models import Vehicle
from geolocation.models import Carrefour, Zone
from rides.models import Ride


class RideLifecycleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        zone = Zone.objects.create(name='Test', city='Yaoundé', is_active=True)
        self.pickup = Carrefour.objects.create(
            id=10, zone=zone, name='Marché Mokolo', city='Yaoundé',
            location=point_from_latlng(3.8744, 11.4988), is_pickup_point=True,
        )
        self.dest = Carrefour.objects.create(
            id=11, zone=zone, name='Rond-point Bastos', city='Yaoundé',
            location=point_from_latlng(3.8872, 11.5144), is_pickup_point=True,
        )
        passenger_role, _ = Role.objects.get_or_create(name='PASSENGER', defaults={'permissions': {}})
        driver_role, _ = Role.objects.get_or_create(name='DRIVER', defaults={'permissions': {}})
        self.passenger = User.objects.create(
            role=passenger_role, first_name='Marie', last_name='P',
            email='lifecycle-pass@test.cm', password_hash='x', is_email_verified=True,
        )
        self.driver = User.objects.create(
            role=driver_role, first_name='Alain', last_name='D',
            email='lifecycle-driver@test.cm', password_hash='x', is_email_verified=True,
            phone='+237690000001',
        )
        UserProfile.objects.create(
            user=self.driver, city='Yaoundé', is_online=True,
            current_lat=3.8750, current_lng=11.4990,
            driver_metadata={'available_seats': 3, 'total_seats': 4},
            cabin_seats=[
                {'seat_id': i, 'seat_name': f'S{i}', 'is_occupied': False} for i in range(1, 5)
            ],
        )
        Vehicle.objects.create(
            registration_number='TEST 001', model='Toyota Jaune',
            capacity_kg=500,
            assigned_driver=self.driver,
        )
        self.passenger_token = create_access_token(self.passenger)
        self.driver_token = create_access_token(self.driver)

    def test_nearby_drivers_and_nearest_carrefour(self):
        r1 = self.client.get('/api/v1/geo/nearest-carrefour', {'lat': 3.8744, 'lng': 11.4988})
        self.assertEqual(r1.status_code, 200)
        self.assertGreater(r1.json()['count'], 0)

        r2 = self.client.get('/api/v1/rides/nearby-drivers', {'lat': 3.8744, 'lng': 11.4988, 'seats': 1})
        self.assertEqual(r2.status_code, 200)
        self.assertIsNotNone(r2.json()['recommended_driver'])

    def test_full_ride_lifecycle(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.passenger_token}')
        r = self.client.post('/api/v1/rides/request', {
            'pickup_carrefour_id': 10,
            'pickup_name': 'Marché Mokolo',
            'destination_carrefour_id': 11,
            'destination_name': 'Rond-point Bastos',
            'ride_type': 'shared',
            'seats_count': 2,
            'payment_method': 'momo',
        }, format='json')
        self.assertEqual(r.status_code, 201)
        ride_id = r.json()['data']['ride_id']
        self.assertEqual(r.json()['data']['status'], 'pending_approval')
        self.assertIsNotNone(r.json()['data']['driver'])

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.driver_token}')
        r2 = self.client.post(f'/api/v1/driver/rides/{ride_id}/approve')
        self.assertEqual(r2.status_code, 200)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.passenger_token}')
        r3 = self.client.post(f'/api/v1/rides/{ride_id}/passenger-arrived')
        self.assertEqual(r3.status_code, 200)

        r4 = self.client.post(f'/api/v1/rides/{ride_id}/board')
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(r4.json()['data']['status'], 'in_trip')

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.driver_token}')
        r5 = self.client.post(f'/api/v1/driver/rides/{ride_id}/complete')
        self.assertEqual(r5.status_code, 200)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.passenger_token}')
        r6 = self.client.post(f'/api/v1/rides/{ride_id}/payment', {
            'phone_number': '+237699112233',
            'payment_method': 'momo',
        }, format='json')
        self.assertEqual(r6.status_code, 200)

        r7 = self.client.post(f'/api/v1/rides/{ride_id}/rate', {'rating': 5}, format='json')
        self.assertEqual(r7.status_code, 200)

        ride = Ride.objects.get(ride_id=ride_id)
        self.assertEqual(ride.status, 'completed')
