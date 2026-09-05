from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from geolocation.services.google_maps import GoogleMapsClient, GoogleMapsError


class GeocodeView(APIView):
    @extend_schema(
        parameters=[OpenApiParameter('address', str, OpenApiParameter.QUERY, required=True)],
        responses={200: dict},
        tags=['Geolocation'],
    )
    def get(self, request):
        address = request.query_params.get('address', '').strip()
        if not address:
            return Response({'detail': 'address query param is required'}, status=400)
        try:
            return Response(GoogleMapsClient().geocode(address))
        except GoogleMapsError as exc:
            return Response({'detail': str(exc), 'status': exc.status}, status=502)


class ReverseGeocodeView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter('lat', float, OpenApiParameter.QUERY, required=True),
            OpenApiParameter('lng', float, OpenApiParameter.QUERY, required=True),
        ],
        responses={200: dict},
        tags=['Geolocation'],
    )
    def get(self, request):
        try:
            lat = float(request.query_params['lat'])
            lng = float(request.query_params['lng'])
        except (KeyError, ValueError):
            return Response({'detail': 'lat and lng query params are required'}, status=400)
        try:
            return Response(GoogleMapsClient().reverse_geocode(lat, lng))
        except GoogleMapsError as exc:
            return Response({'detail': str(exc), 'status': exc.status}, status=502)


class RouteView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter('origin', str, OpenApiParameter.QUERY,
                             description='lat,lng', required=True),
            OpenApiParameter('destination', str, OpenApiParameter.QUERY,
                             description='lat,lng', required=True),
        ],
        responses={200: dict},
        tags=['Geolocation'],
    )
    def get(self, request):
        try:
            o_lat, o_lng = map(float, request.query_params['origin'].split(','))
            d_lat, d_lng = map(float, request.query_params['destination'].split(','))
        except (KeyError, ValueError):
            return Response(
                {'detail': 'origin and destination must be lat,lng pairs'},
                status=400,
            )
        try:
            return Response(GoogleMapsClient().route(o_lat, o_lng, d_lat, d_lng))
        except GoogleMapsError as exc:
            return Response({'detail': str(exc), 'status': exc.status}, status=502)


class CongestionView(APIView):
    @extend_schema(
        parameters=[OpenApiParameter('zone_id', int, OpenApiParameter.QUERY, required=True)],
        responses={200: dict},
        tags=['Geolocation'],
    )
    def get(self, request):
        try:
            zone_id = int(request.query_params['zone_id'])
        except (KeyError, ValueError):
            return Response({'detail': 'zone_id is required'}, status=400)

        from geolocation.models import CongestionSnapshot, Zone

        zone = Zone.objects.filter(pk=zone_id).first()
        if zone is None:
            return Response({'detail': 'Zone not found'}, status=404)

        snapshot = (
            CongestionSnapshot.objects
            .filter(zone_id=zone_id)
            .order_by('-recorded_at')
            .first()
        )
        if snapshot is None:
            return Response({
                'zone_id': zone_id,
                'zone_name': zone.name,
                'congestion_level': 'low',
                'source': 'default',
                'recorded_at': None,
            })
        return Response({
            'zone_id': zone_id,
            'zone_name': zone.name,
            'congestion_level': snapshot.congestion_level,
            'source': snapshot.source,
            'recorded_at': snapshot.recorded_at,
        })
