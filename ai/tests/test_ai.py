"""AI endpoint tests — OpenRouter mocked."""

import json
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role, User, UserProfile
from accounts.services.jwt_service import create_access_token
from config.geo_utils import point_from_latlng
from geolocation.models import Carrefour, Zone


MOCK_PARSE = json.dumps({
    'pickup_carrefour_id': 1,
    'pickup_name': 'Marché Mokolo',
    'destination_carrefour_id': 2,
    'destination_name': 'Rond-point Bastos',
    'ride_type': 'shared',
    'seats_count': 1,
    'payment_method': 'momo',
    'confidence': 0.92,
    'explanation_fr': 'Mokolo vers Bastos, MoMo.',
})

MOCK_RESOLVE = json.dumps({
    'carrefour_id': 1,
    'carrefour_name': 'Marché Mokolo',
    'city': 'Yaoundé',
    'matched_alias': 'mokolo',
    'confidence': 0.95,
    'explanation_fr': 'Alias mokolo → Marché Mokolo',
    'alternatives': [],
})

MOCK_CHAT = 'Le trajet Mokolo–Bastos coûte environ 400 FCFA en partagé (simulation VORA).'

MOCK_BRIEFING = json.dumps({
    'headline_fr': 'Bonne rotation sur Bastos–Poste',
    'recommended_corridor_id': 'Y1',
    'recommended_corridor_name': 'Ligne Principale Bastos - Poste',
    'tips': ['Positionnez-vous tôt au Marché Mokolo'],
    'hot_carrefours': [{'name': 'Marché Mokolo', 'reason_fr': 'Forte demande'}],
    'estimated_rotation_fcfa': 3600,
    'summary_fr': 'Matinee active centre-ville.',
})

MOCK_SOS = json.dumps({
    'category': 'police',
    'urgency': 'critical',
    'summary_fr': 'Passager en danger',
    'recommended_action_fr': 'Contacter 117',
    'authorities_to_notify': ['117', 'patrouille VORA'],
    'passenger_message_fr': 'Aide en route',
})


class AIFeatureTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        zone = Zone.objects.create(name='Test Zone', city='Yaoundé', is_active=True)
        Carrefour.objects.create(
            id=1, zone=zone, name='Marché Mokolo', city='Yaoundé',
            location=point_from_latlng(3.8744, 11.4988), is_pickup_point=True,
        )
        Carrefour.objects.create(
            id=2, zone=zone, name='Rond-point Bastos', city='Yaoundé',
            location=point_from_latlng(3.8872, 11.5144), is_pickup_point=True,
        )
        passenger_role, _ = Role.objects.get_or_create(name='PASSENGER', defaults={'permissions': {}})
        driver_role, _ = Role.objects.get_or_create(name='DRIVER', defaults={'permissions': {}})
        self.passenger = User.objects.create(
            role=passenger_role,
            first_name='Marie',
            last_name='Test',
            email='ai-passenger@test.cm',
            password_hash='x',
            is_email_verified=True,
        )
        self.driver = User.objects.create(
            role=driver_role,
            first_name='Alain',
            last_name='Test',
            email='ai-driver@test.cm',
            password_hash='x',
            is_email_verified=True,
        )
        UserProfile.objects.create(user=self.driver, city='Yaoundé', corridor_axis='Y1')
        self.passenger_token = create_access_token(self.passenger)
        self.driver_token = create_access_token(self.driver)

    @patch('ai.services.features.chat_completion')
    def test_parse_ride(self, mock_chat):
        mock_chat.return_value = MOCK_PARSE
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.passenger_token}')
        r = self.client.post('/api/v1/ai/parse-ride', {
            'text': 'Mokolo vers Bastos, MoMo',
            'city': 'Yaoundé',
        }, format='json')
        self.assertEqual(r.status_code, 200)
        data = r.json()['data']
        self.assertEqual(data['pickup_carrefour_id'], 1)
        self.assertIn('request_payload', data)
        self.assertIn('estimate', data)

    @patch('ai.services.features.chat_completion')
    def test_chat_guide(self, mock_chat):
        mock_chat.return_value = MOCK_CHAT
        r = self.client.post('/api/v1/ai/chat', {
            'messages': [{'role': 'user', 'content': 'Tarif Mokolo Bastos ?'}],
        }, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('400 FCFA', r.json()['data']['content'])

    @patch('ai.services.features.chat_completion')
    def test_resolve_destination(self, mock_chat):
        mock_chat.return_value = MOCK_RESOLVE
        r = self.client.post('/api/v1/ai/resolve-destination', {
            'text': 'mokolo',
            'city': 'Yaoundé',
        }, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['data']['carrefour_id'], 1)

    @patch('ai.services.features.chat_completion')
    def test_driver_briefing(self, mock_chat):
        mock_chat.return_value = MOCK_BRIEFING
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.driver_token}')
        r = self.client.post('/api/v1/ai/driver-briefing', {'city': 'Yaoundé'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['data']['recommended_corridor_id'], 'Y1')

    @patch('ai.services.features.chat_completion')
    def test_classify_sos(self, mock_chat):
        mock_chat.return_value = MOCK_SOS
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.passenger_token}')
        r = self.client.post('/api/v1/ai/classify-sos', {
            'text': 'On me suit dans le taxi',
            'emergency_type': 'police_or_danger',
        }, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['data']['urgency'], 'critical')

    def test_parse_ride_requires_auth(self):
        r = self.client.post('/api/v1/ai/parse-ride', {'text': 'test'}, format='json')
        self.assertIn(r.status_code, (401, 403))

    @patch('ai.services.features.chat_completion')
    def test_ai_not_configured(self, mock_chat):
        from ai.exceptions import AINotConfigured

        mock_chat.side_effect = AINotConfigured('Service IA non configuré.')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.passenger_token}')
        r = self.client.post('/api/v1/ai/parse-ride', {'text': 'test'}, format='json')
        self.assertEqual(r.status_code, 503)
