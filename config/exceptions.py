from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import exception_handler

from accounts.exceptions import VoraAPIException


def vora_exception_handler(exc, context):
    if isinstance(exc, VoraAPIException):
        body = {
            'success': False,
            'error': {
                'code': exc.code,
                'message': str(exc.detail),
            },
            'timestamp': timezone.now().isoformat(),
        }
        if getattr(exc, 'details', None):
            body['error']['details'] = exc.details
        return Response(body, status=exc.status_code)

    response = exception_handler(exc, context)
    if response is None:
        return response

    error_body = {
        'success': False,
        'error': {
            'code': 'REQUEST_FAILED',
            'message': str(exc.detail) if hasattr(exc, 'detail') else str(exc),
        },
        'timestamp': timezone.now().isoformat(),
    }
    if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
        error_body['error']['details'] = exc.detail

    response.data = error_body
    return response
