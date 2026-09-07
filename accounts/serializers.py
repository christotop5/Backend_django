from rest_framework import serializers


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    role = serializers.ChoiceField(choices=['passenger', 'driver'])
    name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    vehicle_plate = serializers.CharField(max_length=30, required=False, allow_blank=True)
    corridor_axis = serializers.CharField(max_length=255, required=False, allow_blank=True)


class OTPSendSerializer(serializers.Serializer):
    email = serializers.EmailField()
    type = serializers.ChoiceField(
        choices=['signup_verification', 'password_reset', 'instant_login'],
        default='signup_verification',
    )


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=4, max_length=4)


class SigninSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class AuthUserSerializer(serializers.Serializer):
    id = serializers.CharField(help_text='Identifiant public, ex. usr_42')
    email = serializers.EmailField()
    name = serializers.CharField()
    role = serializers.ChoiceField(choices=['passenger', 'driver'])
    vehicle_plate = serializers.CharField(required=False, allow_null=True)
    corridor_axis = serializers.CharField(required=False, allow_blank=True)
    redirect_dashboard = serializers.ChoiceField(
        choices=['pickup', 'driver-cockpit'],
        help_text='Route frontend après connexion',
    )
    is_verified = serializers.BooleanField(required=False)


class SigninDataSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField(default='Bearer')
    expires_in = serializers.IntegerField(help_text='Access token TTL en secondes (86400 = 24 h)')
    refresh_expires_in = serializers.IntegerField(help_text='Refresh token TTL en secondes (604800 = 7 j)')
    user = AuthUserSerializer()


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class SigninResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = SigninDataSerializer()


class SignupDataSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    email = serializers.EmailField()
    name = serializers.CharField()
    role = serializers.ChoiceField(choices=['passenger', 'driver'])
    is_verified = serializers.BooleanField()
    otp_sent = serializers.BooleanField()
    otp_expires_in_seconds = serializers.IntegerField()


class SignupResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = SignupDataSerializer()


class OTPVerifyDataSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField(default='Bearer')
    expires_in = serializers.IntegerField()
    refresh_expires_in = serializers.IntegerField()
    user = AuthUserSerializer()


class OTPVerifyResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = OTPVerifyDataSerializer()


class UserMeSerializer(serializers.Serializer):
    id = serializers.CharField()
    email = serializers.EmailField()
    name = serializers.CharField()
    role = serializers.ChoiceField(choices=['passenger', 'driver'])
    phone = serializers.CharField()
    vehicle_plate = serializers.CharField(required=False, allow_null=True)
    corridor_axis = serializers.CharField()
    rating = serializers.FloatField()
    total_rides = serializers.IntegerField()
    wallet_balance_fcfa = serializers.IntegerField()


class MeResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = UserMeSerializer()
