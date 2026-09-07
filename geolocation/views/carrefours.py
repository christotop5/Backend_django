from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response

from config.geo_utils import point_from_latlng
from geolocation.models import Carrefour, Zone
from geolocation.serializers import CarrefourCreateSerializer, CarrefourSerializer


class CarrefourListCreateView(generics.ListAPIView):
    serializer_class = CarrefourSerializer
    pagination_class = None

    @extend_schema(
        tags=['Carrefours'],
        parameters=[
            OpenApiParameter('zone_id', int, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('city', str, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: CarrefourSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = CarrefourSerializer(qs, many=True).data
        return Response(data)

    @extend_schema(request=CarrefourCreateSerializer, responses={201: CarrefourSerializer}, tags=['Carrefours'])
    def post(self, request, *args, **kwargs):
        ser = CarrefourCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        zone = None
        if data.get('zone_id'):
            zone = Zone.objects.filter(pk=data['zone_id']).first()
            if zone is None:
                return Response({'detail': 'Zone not found'}, status=404)
        carrefour = Carrefour.objects.create(
            zone=zone,
            name=data['name'],
            location=point_from_latlng(data['lat'], data['lng']),
            is_pickup_point=data.get('is_pickup_point', True),
        )
        return Response(CarrefourSerializer(carrefour).data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        qs = Carrefour.objects.select_related('zone').order_by('name')
        zone_id = self.request.query_params.get('zone_id')
        city = self.request.query_params.get('city')
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        if city:
            qs = qs.filter(city__icontains=city)
        return qs
