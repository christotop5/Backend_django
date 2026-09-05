"""API tests for VORA Django Geo/Optimization service."""

from unittest.mock import MagicMock, patch

from django.contrib.gis.geos import LineString, Point
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Role, User
from geolocation.models import Carrefour, CongestionSnapshot, DriverTrajectory, Zone
from optimization.models import DemandCache


class VoraAPITestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.role = Role.objects.create(name='DRIVER_TEST', permissions={})
        self.driver = User.objects.create(
            role=self.role,
            first_name='Jean',
            last_name='Driver',
            email='driver_test@vora.local',
            password_hash='hash',
        )
        self.zone = Zone.objects.create(name='Test Zone', is_active=True)
        self.carrefour = Carrefour.objects.create(
            zone=self.zone,
            name='Test Carrefour',
            location=Point(11.5021, 3.8480, srid=4326),
        )


class HealthTests(VoraAPITestBase):
    def test_health(self):
        r = self.client.get('/api/v1/health')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'ok')


class ZoneTests(VoraAPITestBase):
    def test_list_zones(self):
        r = self.client.get('/api/v1/zones')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(any(z['name'] == 'Test Zone' for z in r.json()))

    def test_zone_detail(self):
        r = self.client.get(f'/api/v1/zones/{self.zone.id}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['name'], 'Test Zone')


class CarrefourTests(VoraAPITestBase):
    def test_list_carrefours(self):
        r = self.client.get('/api/v1/carrefours')
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.json()), 1)

    def test_create_carrefour(self):
        r = self.client.post('/api/v1/carrefours', {
            'zone_id': self.zone.id,
            'name': 'New Junction',
            'lat': 3.85,
            'lng': 11.51,
        }, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['name'], 'New Junction')


class TrajectoryTests(VoraAPITestBase):
    def test_create_and_list_trajectory(self):
        r = self.client.post(f'/api/v1/drivers/{self.driver.id}/trajectories', {
            'name': 'Morning turn',
            'points': [
                {'lat': 3.848, 'lng': 11.502},
                {'lat': 3.860, 'lng': 11.520},
            ],
            'tolerance_meters': 500,
        }, format='json')
        self.assertEqual(r.status_code, 201)
        tid = r.json()['id']

        r2 = self.client.get(f'/api/v1/drivers/{self.driver.id}/trajectories')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(len(r2.json()), 1)

        r3 = self.client.get(f'/api/v1/drivers/{self.driver.id}/trajectories/active')
        self.assertEqual(r3.status_code, 200)

        r4 = self.client.delete(f'/api/v1/drivers/{self.driver.id}/trajectories/{tid}')
        self.assertEqual(r4.status_code, 200)


class OptimizationTests(VoraAPITestBase):
    def setUp(self):
        super().setUp()
        self.trajectory = DriverTrajectory.objects.create(
            driver=self.driver,
            name='Route',
            geometry=LineString((11.50, 3.84), (11.52, 3.86), srid=4326),
            tolerance_meters=1000,
        )
        DemandCache.objects.create(
            reservation_id='RES-TEST-001',
            pickup_location=Point(11.501, 3.845, srid=4326),
            destination_location=Point(11.515, 3.855, srid=4326),
            proposed_price=2500,
            status='EN_ATTENTE',
            fetched_at=timezone.now(),
        )

    def test_verify_destination(self):
        r = self.client.post('/api/v1/geo/verify-destination', {
            'driver_id': self.driver.id,
            'destination': {'lat': 3.855, 'lng': 11.515},
        }, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('verified', r.json())

    def test_optimize_turn(self):
        r = self.client.post('/api/v1/optimize/turn', {
            'driver_id': self.driver.id,
        }, format='json')
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body['driver_id'], self.driver.id)
        self.assertGreaterEqual(body['expected_revenue'], 0)

    def test_demand_heatmap(self):
        r = self.client.get(f'/api/v1/optimize/demand-heatmap?zone_id={self.zone.id}')
        self.assertEqual(r.status_code, 200)
        self.assertIn('points', r.json())


class GeoMockedTests(VoraAPITestBase):
    @patch('geolocation.views.geo.GoogleMapsClient')
    def test_geocode(self, mock_cls):
        mock_cls.return_value.geocode.return_value = {
            'address': 'Yaoundé, Cameroon',
            'lat': 3.848,
            'lng': 11.502,
            'place_id': 'abc',
        }
        r = self.client.get('/api/v1/geo/geocode?address=Yaounde')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['lat'], 3.848)

    @patch('geolocation.views.geo.GoogleMapsClient')
    def test_route(self, mock_cls):
        mock_cls.return_value.route.return_value = {
            'distance_meters': 5000,
            'duration_seconds': 900,
            'polyline': 'encoded',
        }
        r = self.client.get('/api/v1/geo/route?origin=3.84,11.50&destination=3.86,11.52')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['distance_meters'], 5000)


class CongestionTests(VoraAPITestBase):
    def test_congestion_default(self):
        r = self.client.get(f'/api/v1/geo/congestion?zone_id={self.zone.id}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['congestion_level'], 'low')

    def test_congestion_with_snapshot(self):
        CongestionSnapshot.objects.create(
            zone=self.zone,
            congestion_level='high',
            source='test',
            recorded_at=timezone.now(),
        )
        r = self.client.get(f'/api/v1/geo/congestion?zone_id={self.zone.id}')
        self.assertEqual(r.json()['congestion_level'], 'high')


class AdminTests(VoraAPITestBase):
    def test_admin_zones(self):
        r = self.client.get('/api/v1/admin/zones')
        self.assertEqual(r.status_code, 200)

    def test_admin_stats(self):
        r = self.client.get('/api/v1/admin/stats')
        self.assertEqual(r.status_code, 200)

    def test_admin_reports(self):
        r = self.client.get('/api/v1/admin/reports')
        self.assertEqual(r.status_code, 200)
