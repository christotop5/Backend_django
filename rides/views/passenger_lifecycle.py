from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.exceptions import NotFound, VoraAPIException
from accounts.models import UserProfile
from rides.models import Ride
from rides.services.map_payload import build_ride_map_payload
from rides.services.seats import occupy_seats_for_ride


def _get_passenger_ride(ride_id: str, passenger) -> Ride:
    ride = Ride.objects.filter(
        ride_id=ride_id, passenger=passenger,
    ).select_related('driver', 'passenger').first()
    if ride is None:
        raise NotFound('Course introuvable.')
    return ride


class RideMapView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rides'])
    def get(self, request, ride_id):
        ride = _get_passenger_ride(ride_id, request.user)
        return Response({'success': True, 'data': build_ride_map_payload(ride, viewer='passenger')})


class PassengerArrivedView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rides'])
    def post(self, request, ride_id):
        ride = _get_passenger_ride(ride_id, request.user)
        if ride.status not in (Ride.Status.APPROVED, Ride.Status.MATCHED):
            raise VoraAPIException(
                'Le chauffeur doit d\'abord accepter la course.',
                code='INVALID_STATE',
            )
        ride.status = Ride.Status.PASSENGER_ARRIVED
        ride.metadata = {
            **ride.metadata,
            'passenger_arrived_at': timezone.now().isoformat(),
        }
        ride.save(update_fields=['status', 'metadata'])
        return Response({
            'success': True,
            'message': 'Position signalée — le chauffeur sait que vous êtes sur place.',
            'data': build_ride_map_payload(ride, viewer='passenger'),
        })


class PassengerBoardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rides'])
    def post(self, request, ride_id):
        ride = _get_passenger_ride(ride_id, request.user)
        if ride.status not in (Ride.Status.PASSENGER_ARRIVED, Ride.Status.APPROVED):
            raise VoraAPIException(
                'Signalez d\'abord votre présence au point de prise en charge.',
                code='INVALID_STATE',
            )
        if not ride.driver_id:
            raise VoraAPIException('Aucun chauffeur assigné.', code='INVALID_STATE')

        profile, _ = UserProfile.objects.get_or_create(user=ride.driver)
        try:
            occupy_seats_for_ride(profile, ride)
        except ValueError as exc:
            raise VoraAPIException(str(exc), code='NO_SEATS_AVAILABLE') from exc
        ride.status = Ride.Status.IN_TRIP
        ride.metadata = {
            **ride.metadata,
            'boarded_at': timezone.now().isoformat(),
        }
        ride.save(update_fields=['status', 'metadata'])
        return Response({
            'success': True,
            'message': f'{ride.seats_count} siège(s) occupé(s). Bon trajet !',
            'data': build_ride_map_payload(ride, viewer='passenger'),
        })
