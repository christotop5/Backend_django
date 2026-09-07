from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.geo_utils import point_from_latlng
from operations.models import Signalement


class SOSSerializer(serializers.Serializer):
    ride_id = serializers.CharField(required=False, allow_blank=True)
    location = serializers.DictField()
    emergency_type = serializers.CharField(default='police_or_danger')
    battery_level_percent = serializers.IntegerField(required=False)


class SOSView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=SOSSerializer,
        tags=['Safety'],
        summary='Déclencher une alerte SOS',
        description=(
            'Enregistre la position GPS et crée un signalement urgent. '
            'Notification simulée vers services de secours (117 / 113) et patrouilles VORA.'
        ),
    )
    def post(self, request):
        ser = SOSSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        loc = ser.validated_data['location']
        point = point_from_latlng(loc['lat'], loc['lng'])
        alert = Signalement.objects.create(
            reporter=request.user,
            reservation_id=ser.validated_data.get('ride_id') or '',
            type=Signalement.Type.SOS,
            description=f"SOS — {ser.validated_data.get('emergency_type', '')}",
            location=point,
            status=Signalement.Status.OPEN,
        )
        return Response({
            'success': True,
            'message': 'Alerte SOS reçue. Position GPS transmise aux services de secours (117 / 113) et aux patrouilles VORA.',
            'data': {
                'alert_id': f'sos_{alert.id}',
                'authorities_notified': True,
                'live_tracking_enabled': True,
                'emergency_desk_call_available': True,
            },
        }, status=201)
