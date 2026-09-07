from rest_framework import serializers


class DriverStatusSerializer(serializers.Serializer):
    is_online = serializers.BooleanField()
    current_location = serializers.DictField(child=serializers.FloatField())


class DriverCorridorSerializer(serializers.Serializer):
    corridor_id = serializers.CharField()
    direction = serializers.ChoiceField(choices=['aller', 'retour'])


class CabinSeatSerializer(serializers.Serializer):
    is_occupied = serializers.BooleanField()
    passenger_type = serializers.ChoiceField(choices=['vora_app', 'street_pickup'], required=False)
    pickup_point = serializers.CharField(required=False, allow_blank=True)
    dropoff_point = serializers.CharField(required=False, allow_blank=True)
    fare_fcfa = serializers.IntegerField(required=False)
    payment_status = serializers.ChoiceField(choices=['paid', 'pending'], required=False)
    payment_method = serializers.ChoiceField(choices=['cash', 'momo'], required=False)


class DriverWithdrawSerializer(serializers.Serializer):
    amount_fcfa = serializers.IntegerField(min_value=500)
    provider = serializers.ChoiceField(choices=['mtn_momo', 'orange_money'])
    phone_number = serializers.CharField(max_length=30)
