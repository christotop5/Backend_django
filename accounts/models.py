from django.db import models


class Role(models.Model):
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    permissions = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roles'

    def __str__(self):
        return self.name


class User(models.Model):
    class TwoFAMethod(models.TextChoices):
        TOTP = 'TOTP', 'TOTP'
        SMS = 'SMS', 'SMS'
        EMAIL = 'email', 'Email'

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='users',
        db_column='role_id',
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=191, unique=True)
    phone = models.CharField(max_length=30, unique=True, blank=True, null=True)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(blank=True, null=True)
    last_login_at = models.DateTimeField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    two_fa_enabled = models.BooleanField(default=False)
    two_fa_method = models.CharField(
        max_length=10,
        choices=TwoFAMethod.choices,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email


class JWTBlacklist(models.Model):
    jti = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blacklisted_tokens',
        db_column='user_id',
    )
    expires_at = models.DateTimeField()
    reason = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'jwt_blacklist'


class RefreshToken(models.Model):
    class ClientType(models.TextChoices):
        DASHBOARD = 'dashboard', 'Dashboard'
        MOBILE = 'mobile', 'Mobile'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='refresh_tokens',
        db_column='user_id',
    )
    token_hash = models.CharField(max_length=255, unique=True)
    client_type = models.CharField(max_length=20, choices=ClientType.choices)
    device_name = models.CharField(max_length=150, blank=True, null=True)
    device_fingerprint = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(blank=True, null=True)
    revoke_reason = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'refresh_tokens'


class TwoFAOTPCode(models.Model):
    class Channel(models.TextChoices):
        SMS = 'SMS', 'SMS'
        EMAIL = 'email', 'Email'

    class Purpose(models.TextChoices):
        LOGIN = 'login', 'Login'
        PASSWORD_RESET = 'password_reset', 'Password reset'
        EMAIL_VERIFY = 'email_verify', 'Email verify'
        PHONE_VERIFY = 'phone_verify', 'Phone verify'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='otp_codes',
        db_column='user_id',
    )
    channel = models.CharField(max_length=10, choices=Channel.choices)
    code_hash = models.CharField(max_length=255)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'two_fa_otp_codes'


class TwoFATOTP(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='totp',
        db_column='user_id',
    )
    secret = models.CharField(max_length=128)
    backup_codes = models.JSONField(default=list)
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'two_fa_totp'


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        db_column='user_id',
    )
    token_hash = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'password_reset_tokens'


class AuditLog(models.Model):
    class ClientType(models.TextChoices):
        DASHBOARD = 'dashboard', 'Dashboard'
        MOBILE = 'mobile', 'Mobile'
        API = 'api', 'API'
        SYSTEM = 'system', 'System'
        ODOO_AUTH = 'odoo_auth', 'Odoo Auth'

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
        db_column='user_id',
        blank=True,
        null=True,
    )
    action = models.CharField(max_length=100, db_index=True)
    resource = models.CharField(max_length=100, blank=True, null=True)
    resource_id = models.CharField(max_length=50, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    client_type = models.CharField(max_length=20, choices=ClientType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'


class Parametre(models.Model):
    id = models.AutoField(primary_key=True)

    class ValueType(models.TextChoices):
        STRING = 'string', 'String'
        INTEGER = 'integer', 'Integer'
        BOOLEAN = 'boolean', 'Boolean'
        JSON = 'json', 'JSON'
        SECRET = 'secret', 'Secret'

    cle = models.CharField(max_length=100, unique=True, db_index=True)
    valeur = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=10, choices=ValueType.choices)
    description = models.CharField(max_length=255, blank=True, null=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='updated_parametres',
        db_column='updated_by',
        blank=True,
        null=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'parametres'

    def __str__(self):
        return self.cle
