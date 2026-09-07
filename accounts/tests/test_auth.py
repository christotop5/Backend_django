"""Auth flow tests — simulated OTP 1234."""

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        Role.objects.get_or_create(name='PASSENGER', defaults={'permissions': {}})
        Role.objects.get_or_create(name='DRIVER', defaults={'permissions': {}})

    def test_signup_otp_signin_flow(self):
        r = self.client.post('/api/v1/auth/signup', {
            'email': 'passenger@vora.cm',
            'password': 'Password123',
            'role': 'passenger',
            'name': 'Alice Passenger',
            'phone': '+237600000001',
        }, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.json()['data']['otp_sent'])

        r2 = self.client.post('/api/v1/auth/otp/verify', {
            'email': 'passenger@vora.cm',
            'otp': '1234',
        }, format='json')
        self.assertEqual(r2.status_code, 200)
        token = r2.json()['data']['access_token']

        r3 = self.client.post('/api/v1/auth/signin', {
            'email': 'passenger@vora.cm',
            'password': 'Password123',
        }, format='json')
        self.assertEqual(r3.status_code, 200)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        r4 = self.client.get('/api/v1/auth/me')
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(r4.json()['data']['role'], 'passenger')

    def test_invalid_otp(self):
        self.client.post('/api/v1/auth/signup', {
            'email': 'badotp@vora.cm',
            'password': 'Password123',
            'role': 'passenger',
            'name': 'Test User',
        }, format='json')
        r = self.client.post('/api/v1/auth/otp/verify', {
            'email': 'badotp@vora.cm',
            'otp': '9999',
        }, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error']['code'], 'INVALID_OTP')

    def test_driver_signup_requires_plate(self):
        r = self.client.post('/api/v1/auth/signup', {
            'email': 'driver@vora.cm',
            'password': 'Password123',
            'role': 'driver',
            'name': 'Jean Driver',
        }, format='json')
        self.assertEqual(r.status_code, 422)
