"""Shared geometry helpers for PostGIS / API payloads."""

from django.contrib.gis.geos import LineString, Point, Polygon


def point_from_latlng(lat: float, lng: float) -> Point:
    return Point(float(lng), float(lat), srid=4326)


def latlng_from_point(point: Point) -> dict:
    return {'lat': point.y, 'lng': point.x}


def linestring_from_points(points: list[dict]) -> LineString:
    coords = [(float(p['lng']), float(p['lat'])) for p in points]
    return LineString(coords, srid=4326)


def linestring_to_points(line: LineString) -> list[dict]:
    return [{'lat': y, 'lng': x} for x, y in line.coords]


def polygon_to_geojson_boundary(polygon: Polygon | None) -> list[dict] | None:
    if polygon is None:
        return None
    ring = polygon[0]
    return [{'lat': y, 'lng': x} for x, y in ring.coords]
