from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from geolocation.models import CorridorLine
from geolocation.serializers import CorridorListResponseSerializer


class CorridorListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter('city', str, OpenApiParameter.QUERY, required=False)],
        responses={200: CorridorListResponseSerializer},
        tags=['Corridors'],
    )
    def get(self, request):
        qs = CorridorLine.objects.filter(is_active=True).order_by('city', 'name')
        city = request.query_params.get('city')
        if city:
            qs = qs.filter(city__icontains=city)
        data = [{
            'id': c.external_id,
            'code': c.code,
            'city': c.city,
            'name': c.name,
            'start_point': c.start_point,
            'end_point': c.end_point,
            'stops': c.stops,
            'standard_fare_fcfa': c.standard_fare_fcfa,
            'distance_km': float(c.distance_km),
            'estimated_duration_min': c.estimated_duration_min,
        } for c in qs]
        return Response({'success': True, 'count': len(data), 'data': data})
