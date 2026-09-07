from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from geolocation.models import Zone
from geolocation.serializers import ZoneDetailSerializer
from operations.models import Signalement, StatistiqueJournaliere


class HealthView(APIView):
    @extend_schema(tags=['System'], responses={200: dict})
    def get(self, request):
        return Response({'status': 'ok', 'service': 'vora-django-geo'})


class AdminZoneListView(APIView):
    @extend_schema(responses={200: ZoneDetailSerializer(many=True)}, tags=['Admin'])
    def get(self, request):
        zones = Zone.objects.all().order_by('name')
        return Response(ZoneDetailSerializer(zones, many=True).data)


class AdminReportsView(APIView):
    @extend_schema(tags=['Admin'], responses={200: dict})
    def get(self, request):
        status_filter = request.query_params.get('status', 'open')
        qs = Signalement.objects.select_related('reporter', 'reported_user').order_by('-created_at')
        if status_filter != 'all':
            qs = qs.filter(status=status_filter)
        reports = [{
            'id': r.id,
            'type': r.type,
            'status': r.status,
            'reporter_id': r.reporter_id,
            'reported_user_id': r.reported_user_id,
            'reservation_id': r.reservation_id,
            'description': r.description,
            'created_at': r.created_at,
        } for r in qs[:100]]
        return Response({'count': len(reports), 'reports': reports})


class AdminStatsView(APIView):
    @extend_schema(tags=['Admin'], responses={200: dict})
    def get(self, request):
        latest = StatistiqueJournaliere.objects.order_by('-date').first()
        open_reports = Signalement.objects.filter(status='open').count()
        if latest:
            return Response({
                'date': latest.date,
                'total_rides': latest.total_rides,
                'total_revenue': float(latest.total_revenue),
                'active_drivers': latest.active_drivers,
                'active_zones': latest.active_zones,
                'open_reports': open_reports,
            })
        return Response({
            'date': None,
            'total_rides': 0,
            'total_revenue': 0,
            'active_drivers': 0,
            'active_zones': Zone.objects.filter(is_active=True).count(),
            'open_reports': open_reports,
        })
