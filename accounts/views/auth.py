from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import (
    MeResponseSerializer,
    OTPSendSerializer,
    OTPVerifyResponseSerializer,
    OTPVerifySerializer,
    SigninResponseSerializer,
    SigninSerializer,
    SignupResponseSerializer,
    SignupSerializer,
)
from accounts.services.auth_service import auth_user_payload, signin, signup, user_me
from accounts.services.jwt_service import create_access_token, create_refresh_token
from accounts.services.otp_service import send_otp, verify_otp


class SignupView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=SignupSerializer,
        responses={201: SignupResponseSerializer},
        tags=['Auth'],
        summary='Créer un compte passager ou chauffeur',
        description=(
            'Inscription avec rôle `passenger` ou `driver`. '
            'Pour les chauffeurs, `vehicle_plate` est obligatoire. '
            'Un OTP est envoyé (simulation) — code fixe **1234**.'
        ),
        examples=[
            OpenApiExample(
                'Passager',
                value={
                    'email': 'marie.ebanda@gmail.com',
                    'password': 'pass12345',
                    'role': 'passenger',
                    'name': 'Marie Ebanda',
                    'phone': '+237699112233',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Chauffeur taxi jaune',
                value={
                    'email': 'alain.mvondo@vora.cm',
                    'password': 'pass12345',
                    'role': 'driver',
                    'name': 'Alain Mvondo',
                    'phone': '+237690123456',
                    'vehicle_plate': 'LT 482 CE',
                    'corridor_axis': 'Poste Centrale ↔ Bastos',
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        ser = SignupSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = signup(ser.validated_data)
        return Response({
            'success': True,
            'message': 'Compte créé avec succès. Veuillez vérifier votre adresse email avec le code OTP.',
            'data': data,
        }, status=status.HTTP_201_CREATED)


class OTPSendView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=OTPSendSerializer,
        tags=['Auth'],
        summary='Renvoyer un code OTP',
        description='Simulation — le code est toujours **1234**. Aucun email réel n\'est envoyé.',
    )
    def post(self, request):
        ser = OTPSendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = send_otp(ser.validated_data['email'], ser.validated_data['type'])
        return Response({
            'success': True,
            'message': 'Code OTP à 4 chiffres envoyé avec succès à votre adresse email.',
            'data': {
                'email': result['email'],
                'expires_at': result['expires_at'],
                'resend_interval_seconds': result['resend_interval_seconds'],
            },
        })


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=OTPVerifySerializer,
        responses={200: OTPVerifyResponseSerializer},
        tags=['Auth'],
        summary='Vérifier le code OTP',
        description='Active le compte et retourne un JWT. Utiliser **1234** en environnement de test.',
        examples=[
            OpenApiExample(
                'Vérification test',
                value={'email': 'marie.ebanda@gmail.com', 'otp': '1234'},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        ser = OTPVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = verify_otp(ser.validated_data['email'], ser.validated_data['otp'])
        return Response({
            'success': True,
            'message': 'Vérification réussie. Votre compte est activé.',
            'data': {
                'access_token': create_access_token(user),
                'refresh_token': create_refresh_token(user),
                'user': auth_user_payload(user),
            },
        })


class SigninView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=SigninSerializer,
        responses={200: SigninResponseSerializer},
        tags=['Auth'],
        summary='Connexion email / mot de passe',
        description=(
            'Retourne un JWT Bearer (24 h) et le profil utilisateur avec `role` et `redirect_dashboard`. '
            'Comptes seed : voir description générale — mot de passe `pass12345`.'
        ),
        examples=[
            OpenApiExample(
                'Passager seed',
                value={'email': 'marie.ebanda@gmail.com', 'password': 'pass12345'},
                request_only=True,
            ),
            OpenApiExample(
                'Chauffeur seed',
                value={'email': 'alain.mvondo@vora.cm', 'password': 'pass12345'},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        ser = SigninSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = signin(ser.validated_data['email'], ser.validated_data['password'])
        return Response({
            'success': True,
            'message': 'Connexion réussie.',
            'data': data,
        })


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: MeResponseSerializer},
        tags=['Auth'],
        summary='Profil utilisateur connecté',
        description='Retourne rôle, solde portefeuille, note et statistiques. Nécessite JWT.',
    )
    def get(self, request):
        return Response({
            'success': True,
            'data': user_me(request.user),
        })
