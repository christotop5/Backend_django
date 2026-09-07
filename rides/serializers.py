from rest_framework import serializers


class RideEstimateSerializer(serializers.Serializer):
    pickup_carrefour_id = serializers.IntegerField()
    destination_carrefour_id = serializers.IntegerField()
    ride_type = serializers.ChoiceField(choices=['shared', 'direct'], default='shared')
    seats_requested = serializers.IntegerField(default=1, min_value=1, max_value=4)


class RideRequestSerializer(serializers.Serializer):
    pickup_carrefour_id = serializers.IntegerField()
    pickup_name = serializers.CharField(max_length=150)
    destination_carrefour_id = serializers.IntegerField()
    destination_name = serializers.CharField(max_length=150)
    ride_type = serializers.ChoiceField(choices=['shared', 'direct'], default='shared')
    seats_count = serializers.IntegerField(default=1, min_value=1, max_value=4)
    payment_method = serializers.ChoiceField(choices=['cash', 'momo', 'om', 'wallet'])
    passenger_notes = serializers.CharField(required=False, allow_blank=True, default='')


class RideRateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    compliments = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    comment = serializers.CharField(required=False, allow_blank=True, default='')
    tip_fcfa = serializers.IntegerField(default=0, min_value=0)
    tip_payment_method = serializers.ChoiceField(
        choices=['momo', 'om', 'cash'],
        required=False,
        default='momo',
    )
