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
    payment_method = serializers.ChoiceField(
        choices=['cash', 'momo', 'om', 'wallet'],
        help_text='Préférence — paiement réel à la fin du trajet uniquement.',
    )
    passenger_notes = serializers.CharField(required=False, allow_blank=True, default='')
    passenger_lat = serializers.FloatField(required=False, allow_null=True)
    passenger_lng = serializers.FloatField(required=False, allow_null=True)


class RidePaymentSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=30, required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(
        choices=['cash', 'momo', 'om', 'wallet'],
        required=False,
    )


class NearbyDriversQuerySerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    seats = serializers.IntegerField(default=1, min_value=1, max_value=4)
    city = serializers.CharField(max_length=50, required=False, allow_blank=True)


class NearestCarrefourQuerySerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    limit = serializers.IntegerField(default=5, min_value=1, max_value=20)
    city = serializers.CharField(max_length=50, required=False, allow_blank=True)


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
