import re

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from accounts.exceptions import (
    AccountNotVerified,
    EmailAlreadyExists,
    InvalidCredentials,
    ValidationFailed,
)
from accounts.models import Role, User, UserProfile
from accounts.services.jwt_service import _role_slug, _user_public_id, create_access_token, create_refresh_token
from accounts.services.otp_service import OTP_TTL_SECONDS, send_otp
from core.models import Vehicle


ROLE_MAP = {
    'passenger': 'PASSENGER',
    'driver': 'DRIVER',
}

REDIRECT_MAP = {
    'passenger': 'pickup',
    'driver': 'driver-cockpit',
}


def _split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(' ', 1)
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], parts[1]


def _ensure_roles():
    for name in ('PASSENGER', 'DRIVER', 'ADMIN', 'CLIENT'):
        Role.objects.get_or_create(name=name, defaults={'permissions': {}})


def _validate_password(password: str) -> dict | None:
    if len(password) < 8:
        return {'password': ['Longueur minimale de 8 caractères requise.']}
    return None


def signup(data: dict) -> dict:
    _ensure_roles()
    email = data['email'].strip().lower()
    role_key = data.get('role', '').lower()
    password = data['password']
    name = data.get('name', '').strip()

    details = {}
    if role_key not in ROLE_MAP:
        details['role'] = ["Doit être 'passenger' ou 'driver'."]
    pwd_err = _validate_password(password)
    if pwd_err:
        details.update(pwd_err)
    if role_key == 'driver' and not data.get('vehicle_plate'):
        details['vehicle_plate'] = ['Requis pour les chauffeurs.']
    if details:
        raise ValidationFailed(
            'Données invalides.',
            details=details,
        )

    if User.objects.filter(email__iexact=email).exists():
        raise EmailAlreadyExists('Un compte existe déjà avec cette adresse email.')

    first_name, last_name = _split_name(name)
    role = Role.objects.get(name=ROLE_MAP[role_key])

    with transaction.atomic():
        user = User.objects.create(
            role=role,
            first_name=first_name or name,
            last_name=last_name,
            email=email,
            phone=data.get('phone') or None,
            password_hash=make_password(password),
            is_email_verified=False,
        )
        UserProfile.objects.create(
            user=user,
            corridor_axis=data.get('corridor_axis', ''),
            wallet_balance_fcfa=28400 if role_key == 'driver' else 0,
        )
        if role_key == 'driver' and data.get('vehicle_plate'):
            Vehicle.objects.create(
                registration_number=data['vehicle_plate'].strip().upper(),
                model='Toyota Yaris Jaune',
                capacity_kg=400,
                assigned_driver=user,
            )

    send_otp(email, 'signup_verification')

    return {
        'user_id': _user_public_id(user),
        'email': user.email,
        'name': name or f'{user.first_name} {user.last_name}'.strip(),
        'role': role_key,
        'is_verified': False,
        'otp_sent': True,
        'otp_expires_in_seconds': OTP_TTL_SECONDS,
    }


def signin(email: str, password: str) -> dict:
    user = User.objects.filter(
        email__iexact=email.strip(),
        deleted_at__isnull=True,
        is_active=True,
    ).select_related('role', 'profile').first()

    if user is None or not check_password(password, user.password_hash):
        raise InvalidCredentials('Adresse email ou mot de passe incorrect.')

    if not user.is_email_verified:
        raise AccountNotVerified(
            'Veuillez vérifier votre compte avec le code OTP envoyé par email.',
        )

    user.last_login_at = timezone.now()
    user.save(update_fields=['last_login_at'])

    role = _role_slug(user)
    profile = getattr(user, 'profile', None)
    vehicle_plate = None
    if role == 'driver':
        vehicle = Vehicle.objects.filter(assigned_driver=user).first()
        vehicle_plate = vehicle.registration_number if vehicle else None

    return {
        'access_token': create_access_token(user),
        'token_type': 'Bearer',
        'expires_in': 86400,
        'user': {
            'id': _user_public_id(user),
            'email': user.email,
            'name': f'{user.first_name} {user.last_name}'.strip(),
            'role': role,
            'vehicle_plate': vehicle_plate,
            'corridor_axis': profile.corridor_axis if profile else '',
            'redirect_dashboard': REDIRECT_MAP.get(role, 'pickup'),
        },
    }


def user_me(user: User) -> dict:
    role = _role_slug(user)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    vehicle_plate = None
    if role == 'driver':
        vehicle = Vehicle.objects.filter(assigned_driver=user).first()
        vehicle_plate = vehicle.registration_number if vehicle else None

    return {
        'id': _user_public_id(user),
        'email': user.email,
        'name': f'{user.first_name} {user.last_name}'.strip(),
        'role': role,
        'phone': user.phone or '',
        'vehicle_plate': vehicle_plate,
        'corridor_axis': profile.corridor_axis,
        'rating': float(profile.rating),
        'total_rides': profile.total_rides,
        'wallet_balance_fcfa': profile.wallet_balance_fcfa,
    }


def auth_user_payload(user: User) -> dict:
    role = _role_slug(user)
    return {
        'id': _user_public_id(user),
        'email': user.email,
        'name': f'{user.first_name} {user.last_name}'.strip(),
        'role': role,
        'is_verified': user.is_email_verified,
        'redirect_dashboard': REDIRECT_MAP.get(role, 'pickup'),
    }
