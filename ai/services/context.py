"""Build geo context from VORA database for LLM prompts."""

from geolocation.models import Carrefour, CorridorLine


def carrefours_catalog(city: str | None = None) -> list[dict]:
    qs = Carrefour.objects.order_by('city', 'name')
    if city:
        qs = qs.filter(city__icontains=city)
    return [
        {
            'id': c.id,
            'name': c.name,
            'city': c.city,
            'zone': c.zone.name if c.zone_id else '',
            'typical_waiting_passengers': c.typical_waiting_passengers,
            'standard_fare_to_centre_fcfa': c.standard_fare_to_centre_fcfa,
        }
        for c in qs.select_related('zone')
    ]


def corridors_catalog(city: str | None = None) -> list[dict]:
    qs = CorridorLine.objects.filter(is_active=True).order_by('city', 'name')
    if city:
        qs = qs.filter(city__icontains=city)
    return [
        {
            'id': c.external_id,
            'code': c.code,
            'city': c.city,
            'name': c.name,
            'stops': c.stops,
            'standard_fare_fcfa': c.standard_fare_fcfa,
        }
        for c in qs
    ]


def format_carrefours_for_prompt(city: str | None = None) -> str:
    lines = []
    for c in carrefours_catalog(city):
        lines.append(
            f"- id={c['id']} | {c['name']} ({c['city']}, {c['zone']}) "
            f"| attente~{c['typical_waiting_passengers']} passagers",
        )
    return '\n'.join(lines) or '(aucun carrefour)'


def format_corridors_for_prompt(city: str | None = None) -> str:
    lines = []
    for c in corridors_catalog(city):
        stops = ' → '.join(c['stops'][:6])
        lines.append(
            f"- {c['id']} ({c['code']}) | {c['name']} | {c['city']} | "
            f"{stops} | {c['standard_fare_fcfa']} FCFA",
        )
    return '\n'.join(lines) or '(aucun corridor)'
