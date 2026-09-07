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
        data2 = r2.json()['data']
        self.assertIn('access_token', data2)
        self.assertIn('refresh_token', data2)
        token = data2['access_token']
        refresh = data2['refresh_token']

        r3 = self.client.post('/api/v1/auth/signin', {
            'email': 'passenger@vora.cm',
            'password': 'Password123',
        }, format='json')
        self.assertEqual(r3.status_code, 200)
        signin_data = r3.json()['data']
        self.assertIn('refresh_token', signin_data)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        r4 = self.client.get('/api/v1/auth/me')
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(r4.json()['data']['role'], 'passenger')

        r5 = self.client.post('/api/v1/auth/refresh', {
            'refresh_token': refresh,
        }, format='json')
        self.assertEqual(r5.status_code, 200)
        new_tokens = r5.json()['data']
        self.assertNotEqual(new_tokens['access_token'], token)
        self.assertNotEqual(new_tokens['refresh_token'], refresh)

        r6 = self.client.post('/api/v1/auth/logout', {
            'refresh_token': new_tokens['refresh_token'],
        }, format='json')
        self.assertEqual(r6.status_code, 200)

        r7 = self.client.post('/api/v1/auth/refresh', {
            'refresh_token': new_tokens['refresh_token'],
        }, format='json')
        self.assertEqual(r7.status_code, 401)
        self.assertEqual(r7.json()['error']['code'], 'INVALID_REFRESH_TOKEN')

    def test_refresh_invalid_token(self):
        r = self.client.post('/api/v1/auth/refresh', {
            'refresh_token': 'invalid-token-value',
        }, format='json')
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()['error']['code'], 'INVALID_REFRESH_TOKEN')

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
