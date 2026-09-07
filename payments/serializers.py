from rest_framework import serializers


class MobilePaymentSerializer(serializers.Serializer):
    amount_fcfa = serializers.IntegerField(min_value=100)
    phone_number = serializers.CharField(max_length=30)
    ride_id = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')
    description = serializers.CharField(required=False, allow_blank=True, default='')


class CashConfirmSerializer(serializers.Serializer):
    amount_fcfa = serializers.IntegerField(min_value=100)
    ride_id = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')


class WalletPaySerializer(serializers.Serializer):
    amount_fcfa = serializers.IntegerField(min_value=100)
    ride_id = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')


class WebhookSerializer(serializers.Serializer):
    provider_ref = serializers.CharField(max_length=128)
    status = serializers.CharField(default='SUCCESS')
