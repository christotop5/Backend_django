import secrets

from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.exceptions import InsufficientFunds
from accounts.models import UserProfile
from accounts.serializers_driver import (
    CabinSeatSerializer,
    DriverCorridorSerializer,
    DriverStatusSerializer,
    DriverWithdrawSerializer,
)
from geolocation.models import Carrefour, CorridorLine

DEFAULT_SEATS = [
    {'seat_id': 1, 'seat_name': 'Avant Passager', 'is_occupied': False},
    {'seat_id': 2, 'seat_name': 'Arrière Gauche', 'is_occupied': False},
    {'seat_id': 3, 'seat_name': 'Arrière Droit', 'is_occupied': False},
    {'seat_id': 4, 'seat_name': 'Arrière Centre', 'is_occupied': False},
]


def _profile(user) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if not profile.cabin_seats:
        profile.cabin_seats = DEFAULT_SEATS.copy()
        profile.save(update_fields=['cabin_seats'])
    return profile


def _resolve_corridor(corridor_id: str) -> CorridorLine | None:
    return CorridorLine.objects.filter(
        Q(external_id=corridor_id) | Q(code=corridor_id),
        is_active=True,
    ).first()


class DriverStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=DriverStatusSerializer, tags=['Driver'])
    def post(self, request):
        ser = DriverStatusSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        profile = _profile(request.user)
        profile.is_online = ser.validated_data['is_online']
        loc = ser.validated_data['current_location']
        profile.current_lat = loc.get('lat')
        profile.current_lng = loc.get('lng')
        profile.save()
        free = sum(1 for s in profile.cabin_seats if not s.get('is_occupied'))
        return Response({
            'success': True,
            'data': {
                'is_online': profile.is_online,
                'active_corridor': profile.active_corridor or 'Bastos ↔ Poste Centrale',
                'free_seats_count': free,
            },
        })


class DriverCorridorView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=DriverCorridorSerializer, tags=['Driver'])
    def post(self, request):
        ser = DriverCorridorSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        profile = _profile(request.user)
        corridor_id = ser.validated_data['corridor_id']
        corridor = _resolve_corridor(corridor_id)
        corridor_name = corridor.name if corridor else corridor_id
        profile.active_corridor = corridor_name
        profile.corridor_axis = corridor_name
        profile.save()

        waiting = 8
        avg_fare = 3600
        if corridor:
            stops = corridor.stops or []
            carrefours = Carrefour.objects.filter(name__in=stops)
            if carrefours.exists():
                waiting = sum(c.typical_waiting_passengers for c in carrefours)
                avg_fare = corridor.standard_fare_fcfa * max(len(stops), 1)

        return Response({
            'success': True,
            'data': {
                'corridor_id': corridor.external_id if corridor else corridor_id,
                'corridor_name': corridor_name,
                'direction': ser.validated_data['direction'],
                'waiting_passengers_count': waiting,
                'avg_fare_rotation_fcfa': avg_fare,
            },
        })


class DriverCabinSeatView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=CabinSeatSerializer, tags=['Driver'])
    def patch(self, request, seat_id):
        ser = CabinSeatSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        profile = _profile(request.user)
        seats = profile.cabin_seats or DEFAULT_SEATS.copy()
        seat = next((s for s in seats if s['seat_id'] == int(seat_id)), None)
        if seat is None:
            seat = {'seat_id': int(seat_id), 'seat_name': f'Siège {seat_id}'}
            seats.append(seat)
        seat.update(ser.validated_data)
        profile.cabin_seats = seats
        profile.save()
        free = sum(1 for s in seats if not s.get('is_occupied'))
        rotation = sum(s.get('fare_fcfa', 0) for s in seats if s.get('is_occupied'))
        return Response({
            'success': True,
            'data': {
                'seat_id': int(seat_id),
                'seat_name': seat.get('seat_name', f'Siège {seat_id}'),
                'is_occupied': seat.get('is_occupied', False),
                'available_seats_remaining': free,
                'current_rotation_total_fcfa': rotation,
            },
        })


class DriverWithdrawView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=DriverWithdrawSerializer, tags=['Driver'])
    def post(self, request):
        ser = DriverWithdrawSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        profile = _profile(request.user)
        amount = ser.validated_data['amount_fcfa']
        if profile.wallet_balance_fcfa < amount:
            raise InsufficientFunds('Solde disponible insuffisant pour ce montant.')
        profile.wallet_balance_fcfa -= amount
        profile.save(update_fields=['wallet_balance_fcfa'])
        return Response({
            'success': True,
            'message': f'Virement Mobile Money simulé de {amount:,} FCFA — aucun argent réel.'.replace(',', ' '),
            'data': {
                'transaction_id': f'tx_{secrets.token_hex(4)}',
                'withdrawn_amount_fcfa': amount,
                'fee_fcfa': 0,
                'remaining_balance_fcfa': profile.wallet_balance_fcfa,
                'status': 'confirmed',
                'simulation': True,
            },
        })
