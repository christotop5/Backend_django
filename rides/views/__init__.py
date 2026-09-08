from drf_spectacular.utils import extend_schema
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.exceptions import NotFound, RideConflict, VoraAPIException
from accounts.models import UserProfile
from geolocation.models import Carrefour
from payments.models import PaymentTransaction
from payments.services.simulation import (
    confirm_cash_payment,
    initiate_mobile_payment,
    pay_with_wallet,
    payment_to_dict,
)
from rides.models import Ride
from rides.serializers import (
    RideEstimateSerializer,
    RidePaymentSerializer,
    RideRateSerializer,
    RideRequestSerializer,
)
from rides.services.map_payload import build_ride_map_payload
from rides.services.matching import match_driver_for_ride
from rides.services.seats import release_seats_for_ride


ACTIVE_PASSENGER_STATUSES = [
    Ride.Status.PENDING_APPROVAL,
    Ride.Status.APPROVED,
    Ride.Status.PASSENGER_ARRIVED,
    Ride.Status.IN_TRIP,
    Ride.Status.AWAITING_PAYMENT,
    Ride.Status.SEARCHING,
    Ride.Status.MATCHED,
    Ride.Status.EN_ROUTE,
]


def _simulate_fare(ride_type: str, seats: int) -> dict:
    base = 400 if ride_type == 'shared' else 1500
    surcharge = 100 * max(seats - 1, 0)
    total = base + surcharge
    if ride_type == 'direct':
        total = 1500
    return {
        'estimated_fare_fcfa': total,
        'base_fare_fcfa': base,
        'seat_surcharge_fcfa': surcharge,
        'estimated_duration_minutes': 14,
        'distance_km': 5.2,
    }


def _process_ride_payment(user, ride: Ride, phone_number: str | None = None) -> dict:
    method = ride.payment_method
    amount = ride.fare_fcfa
    ride_id = ride.ride_id
    phone = phone_number or user.phone or '+237600000000'
    if method == 'cash':
        tx = confirm_cash_payment(user, amount, ride_id)
    elif method == 'momo':
        tx = initiate_mobile_payment(
            user, PaymentTransaction.Provider.MTN_MOMO, amount, phone, ride_id,
        )
    elif method == 'om':
        tx = initiate_mobile_payment(
            user, PaymentTransaction.Provider.ORANGE_MONEY, amount, phone, ride_id,
        )
    elif method == 'wallet':
        tx = pay_with_wallet(user, amount, ride_id)
    else:
        raise VoraAPIException('Méthode de paiement invalide.', code='VALIDATION_FAILED')
    return payment_to_dict(tx)


class RideEstimateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=RideEstimateSerializer, tags=['Rides'])
    def post(self, request):
        ser = RideEstimateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = _simulate_fare(ser.validated_data['ride_type'], ser.validated_data['seats_requested'])
        pickup = Carrefour.objects.filter(pk=ser.validated_data['pickup_carrefour_id']).first()
        if pickup and pickup.location:
            from rides.services.matching import find_nearby_drivers
            loc = {'lat': pickup.location.y, 'lng': pickup.location.x}
            nearby = find_nearby_drivers(loc['lat'], loc['lng'], ser.validated_data['seats_requested'])
            data['available_taxis_count'] = len(nearby)
            data['nearest_taxi_eta_seconds'] = nearby[0]['eta_seconds'] if nearby else None
            data['recommended_driver'] = nearby[0] if nearby else None
        else:
            data['available_taxis_count'] = 0
        return Response({'success': True, 'data': data})


class RideRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=RideRequestSerializer, tags=['Rides'])
    def post(self, request):
        if Ride.objects.filter(
            passenger=request.user,
            status__in=ACTIVE_PASSENGER_STATUSES,
        ).exists():
            raise RideConflict('Une course est déjà en cours pour ce passager.')

        ser = RideRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        pickup = Carrefour.objects.filter(pk=vd['pickup_carrefour_id']).first()
        city = pickup.city if pickup else None

        driver = match_driver_for_ride(vd['pickup_carrefour_id'], vd['seats_count'], city=city)
        if driver is None:
            raise VoraAPIException(
                'Aucun taxi en ligne avec assez de places à proximité.',
                code='NO_DRIVER_AVAILABLE',
                status_code=404,
            )

        fare = _simulate_fare(vd['ride_type'], vd['seats_count'])
        ride = Ride.objects.create(
            ride_id=Ride.generate_id(),
            passenger=request.user,
            driver=driver,
            status=Ride.Status.PENDING_APPROVAL,
            fare_fcfa=fare['estimated_fare_fcfa'],
            metadata={
                'payment_status': 'pending',
                'passenger_lat': vd.get('passenger_lat'),
                'passenger_lng': vd.get('passenger_lng'),
            },
            **{k: vd[k] for k in (
                'pickup_carrefour_id', 'pickup_name', 'destination_carrefour_id',
                'destination_name', 'ride_type', 'seats_count', 'payment_method',
                'passenger_notes',
            )},
        )
        return Response({
            'success': True,
            'message': 'Demande envoyée au chauffeur le plus proche. En attente d\'approbation.',
            'data': {
                **build_ride_map_payload(ride, viewer='passenger'),
                'match_timeout_seconds': 120,
            },
        }, status=status.HTTP_201_CREATED)


class RideStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Rides'])
    def get(self, request, ride_id):
        ride = Ride.objects.filter(
            ride_id=ride_id, passenger=request.user,
        ).select_related('driver', 'passenger').first()
        if ride is None:
            raise NotFound('Course introuvable.')
        payload = build_ride_map_payload(ride, viewer='passenger')
        if ride.driver_id and payload.get('driver'):
            payload['driver']['eta_seconds'] = 120
        return Response({'success': True, 'data': payload})


class RidePayView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=RidePaymentSerializer, tags=['Rides', 'Payments'])
    def post(self, request, ride_id):
        ride = Ride.objects.filter(ride_id=ride_id, passenger=request.user).first()
        if ride is None:
            raise NotFound('Course introuvable.')
        if ride.status != Ride.Status.AWAITING_PAYMENT:
            raise VoraAPIException(
                'Le paiement n\'est possible qu\'à la fin du trajet.',
                code='INVALID_STATE',
            )
        if ride.metadata.get('payment_status') == 'paid':
            raise VoraAPIException('Course déjà payée.', code='ALREADY_PAID')

        ser = RidePaymentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if ser.validated_data.get('payment_method'):
            ride.payment_method = ser.validated_data['payment_method']
            ride.save(update_fields=['payment_method'])

        tx = _process_ride_payment(
            request.user,
            ride,
            phone_number=ser.validated_data.get('phone_number') or None,
        )
        ride.metadata = {
            **ride.metadata,
            'payment_status': 'paid',
            'paid_at': timezone.now().isoformat(),
        }
        ride.save(update_fields=['metadata'])
        return Response({
            'success': True,
            'message': 'Paiement simulé avec succès — aucun argent réel débité.',
            'data': tx,
        })


class RideRateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=RideRateSerializer, tags=['Rides'])
    def post(self, request, ride_id):
        ride = Ride.objects.filter(
            ride_id=ride_id, passenger=request.user,
        ).select_related('driver', 'passenger').first()
        if ride is None:
            raise NotFound('Course introuvable.')
        if ride.metadata.get('payment_status') != 'paid':
            raise VoraAPIException('Payez la course avant de noter.', code='PAYMENT_REQUIRED')

        ser = RideRateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ride.rating = ser.validated_data['rating']
        ride.rating_comment = ser.validated_data.get('comment', '')
        ride.tip_fcfa = ser.validated_data.get('tip_fcfa', 0)
        ride.status = Ride.Status.COMPLETED
        ride.save()

        if ride.driver_id:
            profile, _ = UserProfile.objects.get_or_create(user=ride.driver)
            release_seats_for_ride(profile, ride)

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.total_rides += 1
        profile.save(update_fields=['total_rides'])

        tip_tx = None
        tip = ser.validated_data.get('tip_fcfa', 0)
        if tip > 0:
            method = ser.validated_data.get('tip_payment_method', 'momo')
            if method == 'momo':
                tip_tx = initiate_mobile_payment(
                    request.user, PaymentTransaction.Provider.MTN_MOMO,
                    tip, request.user.phone or '+237600000000', ride.ride_id,
                    description='Pourboire chauffeur (simulation)',
                )
            elif method == 'om':
                tip_tx = initiate_mobile_payment(
                    request.user, PaymentTransaction.Provider.ORANGE_MOMO,
                    tip, request.user.phone or '+237600000000', ride.ride_id,
                    description='Pourboire chauffeur (simulation)',
                )
            else:
                tip_tx = confirm_cash_payment(request.user, tip, ride.ride_id)

        return Response({
            'success': True,
            'message': 'Merci pour votre évaluation !',
            'data': {
                'tip_transferred': bool(tip),
                'tip_payment': payment_to_dict(tip_tx) if tip_tx else None,
            },
        })
