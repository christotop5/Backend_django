"""Google Maps Platform wrapper (Geocoding + Directions)."""

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GEOCODE_URL = 'https://maps.googleapis.com/maps/api/geocode/json'
DIRECTIONS_URL = 'https://maps.googleapis.com/maps/api/directions/json'


class GoogleMapsError(Exception):
    def __init__(self, message: str, status: str = 'ERROR'):
        super().__init__(message)
        self.status = status


class GoogleMapsClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GOOGLE_MAPS_API_KEY
        if not self.api_key:
            raise GoogleMapsError('GOOGLE_MAPS_API_KEY is not configured')

    def _get(self, url: str, params: dict[str, Any]) -> dict:
        params = {**params, 'key': self.api_key}
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.exception('Google Maps API request failed')
            raise GoogleMapsError(str(exc)) from exc
        payload = response.json()
        status = payload.get('status', 'UNKNOWN_ERROR')
        if status not in ('OK', 'ZERO_RESULTS'):
            raise GoogleMapsError(
                payload.get('error_message', status),
                status=status,
            )
        return payload

    def geocode(self, address: str) -> dict:
        payload = self._get(GEOCODE_URL, {'address': address})
        results = payload.get('results', [])
        if not results:
            raise GoogleMapsError('No results found', status='ZERO_RESULTS')
        loc = results[0]['geometry']['location']
        return {
            'address': results[0]['formatted_address'],
            'lat': loc['lat'],
            'lng': loc['lng'],
            'place_id': results[0].get('place_id'),
        }

    def reverse_geocode(self, lat: float, lng: float) -> dict:
        payload = self._get(GEOCODE_URL, {'latlng': f'{lat},{lng}'})
        results = payload.get('results', [])
        if not results:
            raise GoogleMapsError('No results found', status='ZERO_RESULTS')
        loc = results[0]['geometry']['location']
        return {
            'address': results[0]['formatted_address'],
            'lat': loc['lat'],
            'lng': loc['lng'],
            'place_id': results[0].get('place_id'),
        }

    def route(self, origin_lat: float, origin_lng: float,
              dest_lat: float, dest_lng: float) -> dict:
        payload = self._get(DIRECTIONS_URL, {
            'origin': f'{origin_lat},{origin_lng}',
            'destination': f'{dest_lat},{dest_lng}',
            'mode': 'driving',
        })
        routes = payload.get('routes', [])
        if not routes:
            raise GoogleMapsError('No route found', status='ZERO_RESULTS')
        route = routes[0]
        leg = route['legs'][0]
        return {
            'distance_meters': leg['distance']['value'],
            'distance_text': leg['distance']['text'],
            'duration_seconds': leg['duration']['value'],
            'duration_text': leg['duration']['text'],
            'polyline': route['overview_polyline']['points'],
            'start_address': leg['start_address'],
            'end_address': leg['end_address'],
        }
