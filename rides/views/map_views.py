from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rides.serializers import NearestCarrefourQuerySerializer, NearbyDriversQuerySerializer
from rides.services.geo import nearest_carrefours
from rides.services.matching import find_nearby_drivers


class NearestCarrefourView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter('lat', float, OpenApiParameter.QUERY, required=True),
            OpenApiParameter('lng', float, OpenApiParameter.QUERY, required=True),
            OpenApiParameter('limit', int, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('city', str, OpenApiParameter.QUERY, required=False),
        ],
        tags=['Geolocation', 'Rides'],
        summary='Carrefours les plus proches (radar)',
        description='Pour le radar passager — retourne les carrefours triés par distance GPS.',
    )
    def get(self, request):
        ser = NearestCarrefourQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        results = nearest_carrefours(
            data['lat'], data['lng'],
            limit=data.get('limit', 5),
            city=data.get('city') or None,
        )
        return Response({'success': True, 'count': len(results), 'data': results})


class NearbyDriversView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter('lat', float, OpenApiParameter.QUERY, required=True),
            OpenApiParameter('lng', float, OpenApiParameter.QUERY, required=True),
            OpenApiParameter('seats', int, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('city', str, OpenApiParameter.QUERY, required=False),
        ],
        tags=['Rides'],
        summary='Taxis en ligne à proximité (carte)',
        description='Liste réelle des chauffeurs en ligne triés par distance — pour affichage carte avant réservation.',
    )
    def get(self, request):
        ser = NearbyDriversQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        drivers = find_nearby_drivers(
            data['lat'], data['lng'],
            seats_needed=data.get('seats', 1),
            city=data.get('city') or None,
        )
        return Response({
            'success': True,
            'count': len(drivers),
            'data': drivers,
            'recommended_driver': drivers[0] if drivers else None,
        })
