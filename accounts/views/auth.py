from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import (
    OTPSendSerializer,
    OTPVerifySerializer,
    SigninSerializer,
    SignupSerializer,
)
from accounts.services.auth_service import auth_user_payload, signin, signup, user_me
from accounts.services.jwt_service import create_access_token, create_refresh_token
from accounts.services.otp_service import send_otp, verify_otp


class SignupView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=SignupSerializer, tags=['Auth'])
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

    @extend_schema(request=OTPSendSerializer, tags=['Auth'])
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

    @extend_schema(request=OTPVerifySerializer, tags=['Auth'])
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

    @extend_schema(request=SigninSerializer, tags=['Auth'])
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

    @extend_schema(tags=['Auth'])
    def get(self, request):
        return Response({
            'success': True,
            'data': user_me(request.user),
        })
