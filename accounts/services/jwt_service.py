import hashlib
import secrets
from datetime import timedelta

import jwt
from django.conf import settings
from django.utils import timezone

from accounts.models import RefreshToken, User

ACCESS_TOKEN_LIFETIME = timedelta(hours=24)
REFRESH_TOKEN_LIFETIME = timedelta(days=7)
ALGORITHM = 'HS256'


def _user_public_id(user: User) -> str:
    return f'usr_{user.id}'


def create_access_token(user: User) -> str:
    payload = {
        'sub': _user_public_id(user),
        'user_id': user.id,
        'email': user.email,
        'role': _role_slug(user),
        'exp': timezone.now() + ACCESS_TOKEN_LIFETIME,
        'type': 'access',
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user: User, client_type: str = 'mobile') -> str:
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    RefreshToken.objects.create(
        user=user,
        token_hash=token_hash,
        client_type=client_type,
        expires_at=timezone.now() + REFRESH_TOKEN_LIFETIME,
    )
    return raw


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def _role_slug(user: User) -> str:
    name = user.role.name.upper()
    if name == 'DRIVER':
        return 'driver'
    return 'passenger'
