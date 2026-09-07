import hashlib
import secrets
from datetime import timedelta

import jwt
from django.conf import settings
from django.utils import timezone

from accounts.exceptions import InvalidRefreshToken
from accounts.models import RefreshToken, User

ACCESS_TOKEN_LIFETIME = timedelta(hours=24)
REFRESH_TOKEN_LIFETIME = timedelta(days=7)
ALGORITHM = 'HS256'


def _user_public_id(user: User) -> str:
    return f'usr_{user.id}'


def _role_slug(user: User) -> str:
    name = user.role.name.upper()
    if name == 'DRIVER':
        return 'driver'
    return 'passenger'


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


def _hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_refresh_token(user: User, client_type: str = 'mobile') -> str:
    raw = secrets.token_urlsafe(48)
    RefreshToken.objects.create(
        user=user,
        token_hash=_hash_refresh_token(raw),
        client_type=client_type,
        expires_at=timezone.now() + REFRESH_TOKEN_LIFETIME,
    )
    return raw


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def get_refresh_token_record(raw: str) -> RefreshToken:
    token_hash = _hash_refresh_token(raw)
    record = RefreshToken.objects.select_related('user', 'user__role').filter(
        token_hash=token_hash,
        revoked_at__isnull=True,
    ).first()
    if record is None:
        raise InvalidRefreshToken('Refresh token invalide ou révoqué.')
    if record.expires_at <= timezone.now():
        raise InvalidRefreshToken('Refresh token expiré. Veuillez vous reconnecter.')
    if not record.user.is_active or record.user.deleted_at is not None:
        raise InvalidRefreshToken('Compte utilisateur inactif.')
    return record


def revoke_refresh_token(raw: str, reason: str = 'logout') -> None:
    token_hash = _hash_refresh_token(raw)
    record = RefreshToken.objects.filter(token_hash=token_hash, revoked_at__isnull=True).first()
    if record is None:
        raise InvalidRefreshToken('Refresh token invalide ou déjà révoqué.')
    record.revoked_at = timezone.now()
    record.revoke_reason = reason
    record.save(update_fields=['revoked_at', 'revoke_reason'])


def rotate_refresh_token(record: RefreshToken) -> str:
    """Revoke the old refresh token and issue a new one (rotation)."""
    record.revoked_at = timezone.now()
    record.revoke_reason = 'rotated'
    record.save(update_fields=['revoked_at', 'revoke_reason'])
    return create_refresh_token(record.user, client_type=record.client_type)


def refresh_token_pair(raw: str) -> tuple[str, str, User]:
    record = get_refresh_token_record(raw)
    user = record.user
    access = create_access_token(user)
    new_refresh = rotate_refresh_token(record)
    return access, new_refresh, user
