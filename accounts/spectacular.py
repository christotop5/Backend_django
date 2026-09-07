from drf_spectacular.extensions import OpenApiAuthenticationExtension

from accounts.authentication import JWTAuthentication


class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = JWTAuthentication
    name = 'BearerAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': (
                'JWT obtenu via `POST /auth/signin` ou `POST /auth/otp/verify`. '
                'Format header : `Authorization: Bearer <access_token>` — validité 24 h.'
            ),
        }
