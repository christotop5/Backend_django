"""Geo helpers for ride matching and map."""

import math

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D

from config.geo_utils import latlng_from_point, point_from_latlng
from geolocation.models import Carrefour


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def carrefour_latlng(carrefour_id: int) -> dict | None:
    c = Carrefour.objects.filter(pk=carrefour_id).first()
    if c is None or c.location is None:
        return None
    return latlng_from_point(c.location)


def nearest_carrefours(lat: float, lng: float, limit: int = 5, city: str | None = None) -> list[dict]:
    point = point_from_latlng(lat, lng)
    qs = Carrefour.objects.annotate(distance=Distance('location', point)).order_by('distance')
    if city:
        qs = qs.filter(city__icontains=city)
    results = []
    for c in qs[:limit]:
        dist_m = getattr(c, 'distance', None)
        dist_km = round(dist_m.m / 1000, 2) if dist_m is not None else None
        results.append({
            'id': c.id,
            'name': c.name,
            'city': c.city,
            'zone': c.zone.name if c.zone_id else '',
            'location': latlng_from_point(c.location),
            'distance_km': dist_km,
            'distance_m': round(dist_m.m) if dist_m is not None else None,
            'typical_waiting_passengers': c.typical_waiting_passengers,
            'standard_fare_to_centre_fcfa': c.standard_fare_to_centre_fcfa,
        })
    return results
