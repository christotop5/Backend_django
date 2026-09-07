import hashlib
from datetime import timedelta

from django.utils import timezone

from accounts.exceptions import InvalidOTP, RateLimitExceeded, UserNotFound
from accounts.models import TwoFAOTPCode, User

SIMULATED_OTP = '1234'
OTP_TTL_SECONDS = 300
RESEND_INTERVAL_SECONDS = 60

OTP_TYPE_MAP = {
    'signup_verification': TwoFAOTPCode.Purpose.EMAIL_VERIFY,
    'password_reset': TwoFAOTPCode.Purpose.PASSWORD_RESET,
    'instant_login': TwoFAOTPCode.Purpose.LOGIN,
}


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def send_otp(email: str, otp_type: str) -> dict:
    user = User.objects.filter(email__iexact=email, deleted_at__isnull=True).first()
    if user is None:
        raise UserNotFound('Aucun compte associé à cette adresse email.')

    purpose = OTP_TYPE_MAP.get(otp_type, TwoFAOTPCode.Purpose.EMAIL_VERIFY)
    latest = (
        TwoFAOTPCode.objects
        .filter(user=user, purpose=purpose, used_at__isnull=True)
        .order_by('-created_at')
        .first()
    )
    if latest and (timezone.now() - latest.created_at).total_seconds() < RESEND_INTERVAL_SECONDS:
        raise RateLimitExceeded(
            'Veuillez patienter 60 secondes avant de demander un nouveau code OTP.',
        )

    expires_at = timezone.now() + timedelta(seconds=OTP_TTL_SECONDS)
    TwoFAOTPCode.objects.create(
        user=user,
        channel=TwoFAOTPCode.Channel.EMAIL,
        code_hash=_hash_code(SIMULATED_OTP),
        purpose=purpose,
        expires_at=expires_at,
    )

    return {
        'email': user.email,
        'expires_at': expires_at.isoformat(),
        'resend_interval_seconds': RESEND_INTERVAL_SECONDS,
        'simulated_otp': SIMULATED_OTP,  # dev hint — no real email sent
    }


def verify_otp(email: str, otp: str) -> User:
    if otp != SIMULATED_OTP:
        raise InvalidOTP('Le code saisi est incorrect ou a expiré. Veuillez réessayer.')

    user = User.objects.filter(email__iexact=email, deleted_at__isnull=True).first()
    if user is None:
        raise UserNotFound('Aucun compte associé à cette adresse email.')

    record = (
        TwoFAOTPCode.objects
        .filter(user=user, used_at__isnull=True, expires_at__gte=timezone.now())
        .order_by('-created_at')
        .first()
    )
    if record is None:
        raise InvalidOTP('Le code saisi est incorrect ou a expiré. Veuillez réessayer.')

    record.used_at = timezone.now()
    record.save(update_fields=['used_at'])
    user.is_email_verified = True
    user.save(update_fields=['is_email_verified', 'updated_at'])
    return user
