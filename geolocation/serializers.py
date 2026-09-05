from rest_framework import serializers

from geolocation.models import Carrefour, CongestionSnapshot, DriverTrajectory, Zone


class LatLngSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class ZoneListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']


class ZoneDetailSerializer(serializers.ModelSerializer):
    boundary = serializers.SerializerMethodField()
    carrefour_count = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        fields = [
            'id', 'name', 'description', 'boundary', 'is_active',
            'carrefour_count', 'created_at', 'updated_at',
        ]

    def get_boundary(self, obj):
        from config.geo_utils import polygon_to_geojson_boundary
        return polygon_to_geojson_boundary(obj.boundary)

    def get_carrefour_count(self, obj):
        return obj.carrefours.count()


class CarrefourSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()

    class Meta:
        model = Carrefour
        fields = [
            'id', 'zone_id', 'name', 'location', 'is_pickup_point',
            'created_at', 'updated_at',
        ]

    def get_location(self, obj):
        from config.geo_utils import latlng_from_point
        return latlng_from_point(obj.location)


class CarrefourCreateSerializer(serializers.Serializer):
    zone_id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(max_length=150)
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    is_pickup_point = serializers.BooleanField(default=True)


class TrajectorySerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()

    class Meta:
        model = DriverTrajectory
        fields = [
            'id', 'driver_id', 'name', 'geometry', 'tolerance_meters',
            'is_active', 'created_at', 'updated_at',
        ]

    def get_geometry(self, obj):
        from config.geo_utils import linestring_to_points
        return linestring_to_points(obj.geometry)


class TrajectoryCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    points = LatLngSerializer(many=True, min_length=2)
    tolerance_meters = serializers.IntegerField(default=500, min_value=50, max_value=5000)


class TrajectoryUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    points = LatLngSerializer(many=True, min_length=2, required=False)
    tolerance_meters = serializers.IntegerField(required=False, min_value=50, max_value=5000)
    is_active = serializers.BooleanField(required=False)


class CongestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CongestionSnapshot
        fields = ['zone_id', 'congestion_level', 'source', 'recorded_at']
