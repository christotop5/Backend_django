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
