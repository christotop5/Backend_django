from rest_framework import status

from accounts.exceptions import VoraAPIException


class AINotConfigured(VoraAPIException):
    code = 'AI_NOT_CONFIGURED'
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class AIRequestFailed(VoraAPIException):
    code = 'AI_REQUEST_FAILED'
    status_code = status.HTTP_502_BAD_GATEWAY


class AIParseFailed(VoraAPIException):
    code = 'AI_PARSE_FAILED'
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
