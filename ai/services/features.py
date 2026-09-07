"""VORA AI feature implementations."""

from accounts.models import User, UserProfile
from accounts.services.jwt_service import _role_slug
from ai.exceptions import AIParseFailed
from ai.services.context import (
    format_carrefours_for_prompt,
    format_corridors_for_prompt,
)
from ai.services.openrouter import chat_completion, parse_json_response
from ai.services.prompts import (
    DRIVER_BRIEFING_SYSTEM,
    GUIDE_SYSTEM,
    PARSE_RIDE_SYSTEM,
    RESOLVE_DESTINATION_SYSTEM,
    SOS_CLASSIFY_SYSTEM,
)
from geolocation.models import Carrefour, CorridorLine


def _simulate_fare(ride_type: str, seats: int) -> dict:
    base = 400 if ride_type == 'shared' else 1500
    surcharge = 100 * max(seats - 1, 0)
    total = base + surcharge
    if ride_type == 'direct':
        total = 1500
    return {
        'estimated_fare_fcfa': total,
        'base_fare_fcfa': base,
        'seat_surcharge_fcfa': surcharge,
        'estimated_duration_minutes': 14,
        'distance_km': 5.2,
    }


def _validate_carrefour_ids(data: dict) -> dict:
    pickup_id = data.get('pickup_carrefour_id')
    dest_id = data.get('destination_carrefour_id')
    if pickup_id is not None:
        p = Carrefour.objects.filter(pk=pickup_id).first()
        if p:
            data['pickup_name'] = data.get('pickup_name') or p.name
            data['pickup_city'] = p.city
    if dest_id is not None:
        d = Carrefour.objects.filter(pk=dest_id).first()
        if d:
            data['destination_name'] = data.get('destination_name') or d.name
            data['destination_city'] = d.city
    return data


def _validate_single_carrefour(data: dict) -> dict:
    cid = data.get('carrefour_id')
    if cid is not None:
        c = Carrefour.objects.filter(pk=cid).first()
        if c:
            data['carrefour_name'] = data.get('carrefour_name') or c.name
            data['city'] = data.get('city') or c.city
    return data


def parse_ride_from_text(text: str, city: str | None = None) -> dict:
    user_content = f"Ville préférée: {city or 'auto (Yaoundé ou Douala)'}\n\nCarrefours:\n"
    user_content += format_carrefours_for_prompt(city)
    user_content += f"\n\nDemande passager:\n{text}"

    raw = chat_completion(
        [
            {'role': 'system', 'content': PARSE_RIDE_SYSTEM},
            {'role': 'user', 'content': user_content},
        ],
        json_mode=True,
    )
    data = parse_json_response(raw)
    required = (
        'pickup_carrefour_id', 'destination_carrefour_id',
        'ride_type', 'seats_count', 'payment_method',
    )
    missing = [k for k in required if k not in data]
    if missing:
        raise AIParseFailed(
            f'Impossible d\'extraire la course: champs manquants {missing}.',
            details={'raw': data},
        )

    data = _validate_carrefour_ids(data)
    pickup = Carrefour.objects.filter(pk=data['pickup_carrefour_id']).first()
    dest = Carrefour.objects.filter(pk=data['destination_carrefour_id']).first()
    if not pickup or not dest:
        raise AIParseFailed('Carrefour pickup ou destination introuvable en base.')

    seats = min(max(int(data.get('seats_count', 1)), 1), 4)
    ride_type = data.get('ride_type', 'shared')
    if ride_type not in ('shared', 'direct'):
        ride_type = 'shared'
    payment = data.get('payment_method', 'cash')
    if payment not in ('cash', 'momo', 'om', 'wallet'):
        payment = 'cash'

    estimate = _simulate_fare(ride_type, seats)

    return {
        'pickup_carrefour_id': pickup.id,
        'pickup_name': pickup.name,
        'pickup_city': pickup.city,
        'destination_carrefour_id': dest.id,
        'destination_name': dest.name,
        'destination_city': dest.city,
        'ride_type': ride_type,
        'seats_count': seats,
        'payment_method': payment,
        'confidence': float(data.get('confidence', 0.7)),
        'explanation_fr': data.get('explanation_fr', ''),
        'estimate': estimate,
        'ready_for_request': True,
        'request_payload': {
            'pickup_carrefour_id': pickup.id,
            'pickup_name': pickup.name,
            'destination_carrefour_id': dest.id,
            'destination_name': dest.name,
            'ride_type': ride_type,
            'seats_count': seats,
            'payment_method': payment,
        },
    }


def guide_chat(messages: list[dict], user: User | None = None) -> dict:
    system = GUIDE_SYSTEM
    if user:
        role = _role_slug(user)
        system += f"\nUtilisateur connecté: role={role}, email={user.email}."

    llm_messages = [{'role': 'system', 'content': system}]
    for msg in messages[-12:]:
        role = msg.get('role', 'user')
        if role not in ('user', 'assistant'):
            role = 'user'
        llm_messages.append({'role': role, 'content': msg.get('content', '')})

    reply = chat_completion(llm_messages, json_mode=False, temperature=0.4)
    return {
        'role': 'assistant',
        'content': reply,
        'model': 'openrouter',
    }


def resolve_destination(text: str, city: str | None = None, role: str = 'destination') -> dict:
    user_content = (
        f"Rôle: {role} (pickup ou destination)\n"
        f"Ville: {city or 'auto'}\n\nCarrefours:\n"
        f"{format_carrefours_for_prompt(city)}\n\nLieu décrit:\n{text}"
    )
    raw = chat_completion(
        [
            {'role': 'system', 'content': RESOLVE_DESTINATION_SYSTEM},
            {'role': 'user', 'content': user_content},
        ],
        json_mode=True,
    )
    data = parse_json_response(raw)
    if 'carrefour_id' not in data:
        raise AIParseFailed('Impossible de résoudre ce lieu.')
    data = _validate_single_carrefour(data)
    return data


def driver_briefing(user: User, city: str | None = None) -> dict:
    profile = UserProfile.objects.filter(user=user).first()
    driver_city = city or (profile.city if profile else '') or 'Yaoundé'

    online_count = UserProfile.objects.filter(is_online=True, user__role__name='DRIVER').count()
    if city:
        online_count = UserProfile.objects.filter(
            is_online=True, user__role__name='DRIVER', city__icontains=city,
        ).count()

    user_content = (
        f"Chauffeur: {user.first_name} {user.last_name}\n"
        f"Ville: {driver_city}\n"
        f"Corridor actuel: {profile.corridor_axis if profile else 'non défini'}\n"
        f"Chauffeurs en ligne (ville): {online_count}\n\n"
        f"Corridors:\n{format_corridors_for_prompt(driver_city)}\n\n"
        f"Carrefours:\n{format_carrefours_for_prompt(driver_city)}"
    )

    raw = chat_completion(
        [
            {'role': 'system', 'content': DRIVER_BRIEFING_SYSTEM},
            {'role': 'user', 'content': user_content},
        ],
        json_mode=True,
        temperature=0.3,
    )
    data = parse_json_response(raw)

    corridor_id = data.get('recommended_corridor_id')
    corridor = None
    if corridor_id:
        corridor = CorridorLine.objects.filter(external_id=corridor_id, is_active=True).first()
    if corridor is None and data.get('recommended_corridor_name'):
        corridor = CorridorLine.objects.filter(
            name__icontains=data['recommended_corridor_name'][:20],
            is_active=True,
        ).first()
    if corridor:
        data['recommended_corridor_id'] = corridor.external_id
        data['recommended_corridor_name'] = corridor.name
        data['corridor_code'] = corridor.code

    data['city'] = driver_city
    data['online_drivers_count'] = online_count
    return data


def classify_sos(text: str, emergency_type: str | None = None, location: dict | None = None) -> dict:
    loc_str = ''
    if location:
        loc_str = f"GPS: lat={location.get('lat')}, lng={location.get('lng')}"
    user_content = (
        f"Type déclaré: {emergency_type or 'non précisé'}\n"
        f"{loc_str}\n\nDescription / message passager:\n{text or '(aucun texte)'}"
    )
    raw = chat_completion(
        [
            {'role': 'system', 'content': SOS_CLASSIFY_SYSTEM},
            {'role': 'user', 'content': user_content},
        ],
        json_mode=True,
        temperature=0.1,
    )
    return parse_json_response(raw)
