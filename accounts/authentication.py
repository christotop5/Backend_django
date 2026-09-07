import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from accounts.models import User
from accounts.services.jwt_service import decode_access_token


class JWTAuthentication(BaseAuthentication):
    keyword = 'Bearer'

    def authenticate(self, request):
        header = request.headers.get('Authorization', '')
        if not header.startswith(f'{self.keyword} '):
            return None
        token = header[len(self.keyword) + 1:]
        try:
            payload = decode_access_token(token)
        except jwt.PyJWTError as exc:
            raise AuthenticationFailed('Token invalide ou expiré.') from exc

        user_id = payload.get('user_id')
        if not user_id:
            raise AuthenticationFailed('Token invalide.')

        user = User.objects.filter(pk=user_id, is_active=True, deleted_at__isnull=True).first()
        if user is None:
            raise AuthenticationFailed('Utilisateur introuvable.')
        return user, token
