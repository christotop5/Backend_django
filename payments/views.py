from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.exceptions import NotFound
from payments.models import PaymentTransaction
from payments.serializers import CashConfirmSerializer, MobilePaymentSerializer, WebhookSerializer
from payments.services.simulation import (
    SIMULATION_NOTE,
    confirm_cash_payment,
    get_payment_status,
    initiate_mobile_payment,
    payment_to_dict,
    simulate_webhook_confirm,
)


class MTNMomoPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MobilePaymentSerializer,
        tags=['Payments'],
        summary='Paiement MTN MoMo simulé',
        description='Aucun débit réel. Retourne `simulation: true` et un `transaction_id` de test.',
    )
    def post(self, request):
        ser = MobilePaymentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tx = initiate_mobile_payment(
            user=request.user,
            provider=PaymentTransaction.Provider.MTN_MOMO,
            **ser.validated_data,
        )
        return Response({
            'success': True,
            'message': f'Paiement MTN MoMo simulé avec succès. {SIMULATION_NOTE}',
            'data': payment_to_dict(tx),
        }, status=status.HTTP_201_CREATED)


class OrangeMoneyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MobilePaymentSerializer,
        tags=['Payments'],
        summary='Paiement Orange Money simulé',
        description='Aucun débit réel. Retourne `simulation: true` et un `transaction_id` de test.',
    )
    def post(self, request):
        ser = MobilePaymentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tx = initiate_mobile_payment(
            user=request.user,
            provider=PaymentTransaction.Provider.ORANGE_MONEY,
            **ser.validated_data,
        )
        return Response({
            'success': True,
            'message': f'Paiement Orange Money simulé avec succès. {SIMULATION_NOTE}',
            'data': payment_to_dict(tx),
        }, status=status.HTTP_201_CREATED)


class CashConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CashConfirmSerializer,
        tags=['Payments'],
        summary='Confirmer paiement espèces',
        description='Enregistre un paiement cash simulé (chauffeur ou passager).',
    )
    def post(self, request):
        ser = CashConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tx = confirm_cash_payment(user=request.user, **ser.validated_data)
        return Response({
            'success': True,
            'message': 'Paiement espèces enregistré (simulation).',
            'data': payment_to_dict(tx),
        })


class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Payments'],
        summary='Statut d\'une transaction',
        description='Interroge l\'état d\'un paiement simulé par `transaction_id`.',
    )
    def get(self, request, transaction_id):
        tx = get_payment_status(transaction_id, user=request.user)
        return Response({'success': True, 'data': payment_to_dict(tx)})


class OrangeWebhookView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=WebhookSerializer, tags=['Payments'])
    def post(self, request):
        ser = WebhookSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tx = simulate_webhook_confirm(ser.validated_data['provider_ref'])
        if tx is None:
            raise NotFound('Transaction introuvable.')
        return Response({'success': True, 'data': payment_to_dict(tx)})


class MTNWebhookView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=WebhookSerializer, tags=['Payments'])
    def post(self, request):
        ser = WebhookSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tx = simulate_webhook_confirm(ser.validated_data['provider_ref'])
        if tx is None:
            raise NotFound('Transaction introuvable.')
        return Response({'success': True, 'data': payment_to_dict(tx)})
