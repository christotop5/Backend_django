from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.geo_utils import latlng_from_point, point_from_latlng
from optimization.serializers import OptimizeTurnSerializer, VerifyDestinationSerializer
from optimization.services.corridor import demand_in_zone
from optimization.services.corridor import destination_within_corridor
from optimization.services.turn_optimizer import optimize_turn


class VerifyDestinationView(APIView):
    @extend_schema(
        request=VerifyDestinationSerializer,
        responses={200: dict},
        tags=['Optimization'],
        description='Used by Spring Boot during matching. Checks ST_DWithin corridor.',
    )
    def post(self, request):
        ser = VerifyDestinationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        dest = data['destination']
        result = destination_within_corridor(
            driver_id=data['driver_id'],
            destination=point_from_latlng(dest['lat'], dest['lng']),
            tolerance_meters=data.get('tolerance_meters'),
        )
        return Response(result)


class OptimizeTurnView(APIView):
    @extend_schema(
        request=OptimizeTurnSerializer,
        responses={200: dict},
        tags=['Optimization'],
        description='Core turn optimizer — greedy corridor matching.',
    )
    def post(self, request):
        ser = OptimizeTurnSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        result = optimize_turn(
            driver_id=data['driver_id'],
            zone_id=data.get('zone_id'),
        )
        return Response(result)


class DemandHeatmapView(APIView):
    @extend_schema(
        parameters=[],
        responses={200: dict},
        tags=['Optimization'],
    )
    def get(self, request):
        zone_id = request.query_params.get('zone_id')
        if not zone_id:
            return Response({'detail': 'zone_id is required'}, status=400)
        try:
            zone_id = int(zone_id)
        except ValueError:
            return Response({'detail': 'zone_id must be an integer'}, status=400)

        demands = demand_in_zone(zone_id)
        points = [{
            'reservation_id': d.reservation_id,
            'pickup': latlng_from_point(d.pickup_location),
            'destination': latlng_from_point(d.destination_location),
            'proposed_price': float(d.proposed_price),
            'status': d.status,
        } for d in demands]
        return Response({'zone_id': zone_id, 'count': len(points), 'points': points})
