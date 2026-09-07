from rest_framework import status
from rest_framework.exceptions import APIException


class VoraAPIException(APIException):
    code = 'ERROR'
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message, code=None, details=None, status_code=None):
        self.code = code or self.code
        if status_code:
            self.status_code = status_code
        self.details = details
        super().__init__(message)


class EmailAlreadyExists(VoraAPIException):
    code = 'EMAIL_ALREADY_EXISTS'
    status_code = status.HTTP_409_CONFLICT


class ValidationFailed(VoraAPIException):
    code = 'VALIDATION_FAILED'
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class UserNotFound(VoraAPIException):
    code = 'USER_NOT_FOUND'
    status_code = status.HTTP_404_NOT_FOUND


class RateLimitExceeded(VoraAPIException):
    code = 'RATE_LIMIT_EXCEEDED'
    status_code = status.HTTP_429_TOO_MANY_REQUESTS


class InvalidOTP(VoraAPIException):
    code = 'INVALID_OTP'
    status_code = status.HTTP_400_BAD_REQUEST


class InvalidCredentials(VoraAPIException):
    code = 'INVALID_CREDENTIALS'
    status_code = status.HTTP_401_UNAUTHORIZED


class InvalidRefreshToken(VoraAPIException):
    code = 'INVALID_REFRESH_TOKEN'
    status_code = status.HTTP_401_UNAUTHORIZED


class AccountNotVerified(VoraAPIException):
    code = 'ACCOUNT_NOT_VERIFIED'
    status_code = status.HTTP_403_FORBIDDEN


class InsufficientFunds(VoraAPIException):
    code = 'INSUFFICIENT_FUNDS'
    status_code = status.HTTP_400_BAD_REQUEST


class RideConflict(VoraAPIException):
    code = 'RIDE_ALREADY_ACTIVE'
    status_code = status.HTTP_409_CONFLICT


class NotFound(VoraAPIException):
    code = 'NOT_FOUND'
    status_code = status.HTTP_404_NOT_FOUND
