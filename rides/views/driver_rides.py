from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.exceptions import NotFound, VoraAPIException
from accounts.services.jwt_service import _role_slug
from rides.models import Ride
from rides.services.map_payload import build_ride_map_payload


def _require_driver(user):
    if _role_slug(user) != 'driver':
        raise VoraAPIException('Réservé aux chauffeurs.', code='FORBIDDEN', status_code=403)


def _get_driver_ride(ride_id: str, driver) -> Ride:
    ride = Ride.objects.filter(ride_id=ride_id, driver=driver).select_related('passenger').first()
    if ride is None:
        raise NotFound('Course introuvable pour ce chauffeur.')
    return ride


class DriverPendingRidesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rides', 'Driver'])
    def get(self, request):
        _require_driver(request.user)
        rides = Ride.objects.filter(
            driver=request.user,
            status=Ride.Status.PENDING_APPROVAL,
        ).select_related('passenger').order_by('-created_at')
        data = [build_ride_map_payload(r, viewer='driver') for r in rides]
        return Response({'success': True, 'count': len(data), 'data': data})


class DriverActiveRidesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rides', 'Driver'])
    def get(self, request):
        _require_driver(request.user)
        active_statuses = [
            Ride.Status.APPROVED,
            Ride.Status.PASSENGER_ARRIVED,
            Ride.Status.IN_TRIP,
            Ride.Status.AWAITING_PAYMENT,
            Ride.Status.MATCHED,
            Ride.Status.EN_ROUTE,
        ]
        rides = Ride.objects.filter(
            driver=request.user,
            status__in=active_statuses,
        ).select_related('passenger').order_by('-updated_at')
        data = [build_ride_map_payload(r, viewer='driver') for r in rides]
        return Response({'success': True, 'count': len(data), 'data': data})


class DriverRideMapView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rides', 'Driver'])
    def get(self, request, ride_id):
        _require_driver(request.user)
        ride = _get_driver_ride(ride_id, request.user)
        return Response({'success': True, 'data': build_ride_map_payload(ride, viewer='driver')})


class DriverApproveRideView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rides', 'Driver'])
    def post(self, request, ride_id):
        _require_driver(request.user)
        ride = _get_driver_ride(ride_id, request.user)
        if ride.status != Ride.Status.PENDING_APPROVAL:
            raise VoraAPIException('Cette course n\'attend plus d\'approbation.', code='INVALID_STATE')
        ride.status = Ride.Status.APPROVED
        ride.metadata = {
            **ride.metadata,
            'driver_approved_at': timezone.now().isoformat(),
        }
        ride.save(update_fields=['status', 'metadata'])
        return Response({
            'success': True,
            'message': 'Course acceptée. Le passager peut se rendre au point de prise en charge.',
            'data': build_ride_map_payload(ride, viewer='driver'),
        })


class DriverRejectRideView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rides', 'Driver'])
    def post(self, request, ride_id):
        _require_driver(request.user)
        ride = _get_driver_ride(ride_id, request.user)
        if ride.status != Ride.Status.PENDING_APPROVAL:
            raise VoraAPIException('Cette course n\'attend plus d\'approbation.', code='INVALID_STATE')
        ride.status = Ride.Status.REJECTED
        ride.driver = None
        ride.save(update_fields=['status', 'driver'])
        return Response({'success': True, 'message': 'Course refusée.'})


class DriverCompleteRideView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rides', 'Driver'])
    def post(self, request, ride_id):
        _require_driver(request.user)
        ride = _get_driver_ride(ride_id, request.user)
        if ride.status != Ride.Status.IN_TRIP:
            raise VoraAPIException('La course n\'est pas en cours.', code='INVALID_STATE')
        ride.status = Ride.Status.AWAITING_PAYMENT
        ride.metadata = {
            **ride.metadata,
            'trip_ended_at': timezone.now().isoformat(),
            'payment_status': 'pending',
        }
        ride.save(update_fields=['status', 'metadata'])
        return Response({
            'success': True,
            'message': 'Trajet terminé. En attente du paiement passager.',
            'data': build_ride_map_payload(ride, viewer='driver'),
        })
