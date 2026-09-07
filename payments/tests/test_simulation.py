"""Simulated payment tests — no real money."""

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role, User, UserProfile
from django.contrib.auth.hashers import make_password


class PaymentSimulationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        role, _ = Role.objects.get_or_create(name='PASSENGER', defaults={'permissions': {}})
        self.user = User.objects.create(
            role=role,
            first_name='Pay',
            last_name='Test',
            email='paytest@vora.cm',
            password_hash=make_password('Password123'),
            is_email_verified=True,
            phone='+237600000099',
        )
        UserProfile.objects.create(user=self.user, wallet_balance_fcfa=5000)

    def _auth(self):
        from accounts.services.jwt_service import create_access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {create_access_token(self.user)}')

    def test_mtn_momo_simulation(self):
        self._auth()
        r = self.client.post('/api/v1/payments/mtn-momo', {
            'amount_fcfa': 500,
            'phone_number': '+237677241892',
            'ride_id': 'rd_test01',
        }, format='json')
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertTrue(body['success'])
        self.assertTrue(body['data']['simulation'])
        self.assertEqual(body['data']['status'], 'confirmed')

    def test_orange_money_simulation(self):
        self._auth()
        r = self.client.post('/api/v1/payments/orange-money', {
            'amount_fcfa': 400,
            'phone_number': '+237699112233',
        }, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['data']['provider'], 'orange_money')

    def test_wallet_insufficient(self):
        self._auth()
        from payments.services.simulation import pay_with_wallet
        from accounts.exceptions import InsufficientFunds
        with self.assertRaises(InsufficientFunds):
            pay_with_wallet(self.user, 99999)

    def test_payment_status(self):
        self._auth()
        r = self.client.post('/api/v1/payments/cash/confirm', {
            'amount_fcfa': 500,
            'ride_id': 'rd_cash01',
        }, format='json')
        tx_id = r.json()['data']['transaction_id']
        r2 = self.client.get(f'/api/v1/payments/{tx_id}/status')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()['data']['status'], 'confirmed')
