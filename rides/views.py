from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.exceptions import NotFound
from accounts.models import UserProfile
from payments.models import PaymentTransaction
from payments.serializers import WalletPaySerializer
from payments.services.simulation import (
    confirm_cash_payment,
    initiate_mobile_payment,
    pay_with_wallet,
    payment_to_dict,
)
from rides.models import Ride
from rides.serializers import RideEstimateSerializer, RideRateSerializer, RideRequestSerializer


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
        'available_taxis_count': 7,
        'nearest_taxi_eta_seconds': 180,
    }


def _process_ride_payment(user, ride: Ride) -> dict | None:
    method = ride.payment_method
    amount = ride.fare_fcfa
    ride_id = ride.ride_id
    if method == 'cash':
        tx = confirm_cash_payment(user, amount, ride_id)
    elif method == 'momo':
        tx = initiate_mobile_payment(
            user, PaymentTransaction.Provider.MTN_MOMO,
            amount, user.phone or '+237600000000', ride_id,
        )
    elif method == 'om':
        tx = initiate_mobile_payment(
            user, PaymentTransaction.Provider.ORANGE_MONEY,
            amount, user.phone or '+237600000000', ride_id,
        )
    elif method == 'wallet':
        tx = pay_with_wallet(user, amount, ride_id)
    else:
        return None
    return payment_to_dict(tx)


class RideEstimateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=RideEstimateSerializer,
        tags=['Rides'],
        summary='Estimer le tarif d\'une course',
        description='Calcule tarif partagé ou direct entre deux carrefours seedés (`GET /carrefours`).',
        examples=[
            OpenApiExample(
                'Poste Centrale → Bastos (partagé)',
                value={
                    'pickup_carrefour_id': 1,
                    'destination_carrefour_id': 2,
                    'ride_type': 'shared',
                    'seats_requested': 1,
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        ser = RideEstimateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = _simulate_fare(ser.validated_data['ride_type'], ser.validated_data['seats_requested'])
        return Response({'success': True, 'data': data})


class RideRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=RideRequestSerializer,
        tags=['Rides'],
        summary='Demander une course',
        description=(
            'Crée une course et simule le matching taxi jaune. '
            'Paiement momo/om/wallet déclenché immédiatement ; espèces à l\'arrivée.'
        ),
    )
    def post(self, request):
        from accounts.exceptions import RideConflict

        active = Ride.objects.filter(
            passenger=request.user,
            status__in=[Ride.Status.SEARCHING, Ride.Status.MATCHED, Ride.Status.EN_ROUTE, Ride.Status.IN_TRIP],
        ).exists()
        if active:
            raise RideConflict('Une course est déjà en cours pour ce passager.')

        ser = RideRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        fare = _simulate_fare(ser.validated_data['ride_type'], ser.validated_data['seats_count'])
        ride = Ride.objects.create(
            ride_id=Ride.generate_id(),
            passenger=request.user,
            status=Ride.Status.SEARCHING,
            fare_fcfa=fare['estimated_fare_fcfa'],
            **ser.validated_data,
        )
        ride.status = Ride.Status.MATCHED
        ride.save(update_fields=['status'])
        payment_info = None
        if ser.validated_data['payment_method'] != 'cash':
            payment_info = _process_ride_payment(request.user, ride)
        return Response({
            'success': True,
            'message': "Recherche de taxi jaune en cours sur l'axe...",
            'data': {
                'ride_id': ride.ride_id,
                'status': ride.status,
                'fare_fcfa': ride.fare_fcfa,
                'match_timeout_seconds': 120,
                'payment': payment_info,
            },
        }, status=status.HTTP_201_CREATED)


class RideStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Rides'],
        summary='Statut course & infos chauffeur',
        description='Polling du statut. Retourne un chauffeur simulé avec position et ETA.',
    )
    def get(self, request, ride_id):
        ride = Ride.objects.filter(ride_id=ride_id, passenger=request.user).first()
        if ride is None:
            raise NotFound('Course introuvable.')
        return Response({
            'success': True,
            'data': {
                'ride_id': ride.ride_id,
                'status': ride.status,
                'payment_method': ride.payment_method,
                'driver': {
                    'name': 'Talla Rodrigue',
                    'phone': '+237699112233',
                    'vehicle_plate': 'CE 841 AZ',
                    'car_model': 'Toyota Yaris Jaune',
                    'rating': 4.93,
                    'current_lat': 3.8682,
                    'current_lng': 11.5175,
                    'eta_seconds': 120,
                    'occupied_seats': 2,
                    'total_seats': 4,
                },
            },
        })


class RidePayView(APIView):
    """Pay for a ride at arrival — simulation only."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Rides', 'Payments'],
        summary='Payer la course à l\'arrivée',
        description='Simulation — déclenche le paiement selon la méthode enregistrée sur la course.',
    )
    def post(self, request, ride_id):
        ride = Ride.objects.filter(ride_id=ride_id, passenger=request.user).first()
        if ride is None:
            raise NotFound('Course introuvable.')
        tx = _process_ride_payment(request.user, ride)
        return Response({
            'success': True,
            'message': 'Paiement simulé avec succès — aucun argent réel débité.',
            'data': tx,
        })


class RideRateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=RideRateSerializer,
        tags=['Rides'],
        summary='Noter le chauffeur et laisser un pourboire',
        description='Clôture la course, enregistre la note et simule le transfert du pourboire.',
    )
    def post(self, request, ride_id):
        ride = Ride.objects.filter(ride_id=ride_id, passenger=request.user).first()
        if ride is None:
            raise NotFound('Course introuvable.')
        ser = RideRateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ride.rating = ser.validated_data['rating']
        ride.rating_comment = ser.validated_data.get('comment', '')
        ride.tip_fcfa = ser.validated_data.get('tip_fcfa', 0)
        ride.status = Ride.Status.COMPLETED
        ride.save()

        if ride.payment_method == 'cash' and ride.fare_fcfa:
            confirm_cash_payment(request.user, ride.fare_fcfa, ride.ride_id)

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
                    request.user, PaymentTransaction.Provider.ORANGE_MONEY,
                    tip, request.user.phone or '+237600000000', ride.ride_id,
                    description='Pourboire chauffeur (simulation)',
                )
            else:
                tip_tx = confirm_cash_payment(request.user, tip, ride.ride_id)

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.total_rides += 1
        profile.save(update_fields=['total_rides'])
        return Response({
            'success': True,
            'message': 'Merci pour votre évaluation ! Le pourboire a été transféré au chauffeur (simulation).',
            'data': {
                'driver_new_rating': 4.94,
                'tip_transferred': bool(tip),
                'tip_payment': payment_to_dict(tip_tx) if tip_tx else None,
            },
        })
