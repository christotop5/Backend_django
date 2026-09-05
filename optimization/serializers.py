from rest_framework import serializers


class LatLngSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class VerifyDestinationSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField()
    destination = LatLngSerializer()
    tolerance_meters = serializers.IntegerField(required=False, min_value=50, max_value=5000)


class OptimizeTurnSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField()
    zone_id = serializers.IntegerField(required=False)


class DemandHeatmapPointSerializer(serializers.Serializer):
    reservation_id = serializers.CharField()
    pickup = LatLngSerializer()
    destination = LatLngSerializer()
    proposed_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()
