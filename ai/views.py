from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.exceptions import VoraAPIException
from accounts.services.jwt_service import _role_slug
from ai.serializers import (
    ChatRequestSerializer,
    ClassifySOSRequestSerializer,
    DriverBriefingRequestSerializer,
    ParseRideRequestSerializer,
    ResolveDestinationRequestSerializer,
)
from ai.services.features import (
    classify_sos,
    driver_briefing,
    guide_chat,
    parse_ride_from_text,
    resolve_destination,
)


def _require_driver(user):
    if _role_slug(user) != 'driver':
        raise VoraAPIException(
            'Réservé aux chauffeurs.',
            code='FORBIDDEN',
            status_code=403,
        )


class ParseRideAIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ParseRideRequestSerializer,
        tags=['AI'],
        summary='Langage naturel → course structurée',
        description=(
            'Convertit une phrase passager en carrefours + paramètres `/rides/request`. '
            'Inclut une estimation tarifaire simulée.'
        ),
        examples=[
            OpenApiExample(
                'Demande Mokolo → Bastos',
                value={
                    'text': 'Je suis au Mokolo, je vais à Bastos, 1 place, paiement MTN MoMo',
                    'city': 'Yaoundé',
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        ser = ParseRideRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        city = ser.validated_data.get('city') or None
        data = parse_ride_from_text(ser.validated_data['text'], city=city)
        return Response({'success': True, 'data': data})


class ChatAIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ChatRequestSerializer,
        tags=['AI'],
        summary='VORA Guide — chatbot',
        description='Assistant conversationnel pour passagers et chauffeurs (FR / contexte Cameroun).',
        examples=[
            OpenApiExample(
                'Question tarif',
                value={
                    'messages': [{'role': 'user', 'content': 'C\'est combien de Mokolo à Bastos en partagé ?'}],
                    'city': 'Yaoundé',
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        ser = ChatRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user if getattr(request.user, 'is_authenticated', False) else None
        reply = guide_chat(ser.validated_data['messages'], user=user)
        return Response({'success': True, 'data': reply})


class ResolveDestinationAIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ResolveDestinationRequestSerializer,
        tags=['AI'],
        summary='Résoudre un surnom de lieu → carrefour',
        description='Alias locaux (mokolo, deido, campus…) vers un carrefour VORA avec alternatives.',
        examples=[
            OpenApiExample(
                'Surnom local',
                value={'text': 'je go wanda', 'city': 'Yaoundé', 'role': 'pickup'},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        ser = ResolveDestinationRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        city = ser.validated_data.get('city') or None
        data = resolve_destination(
            ser.validated_data['text'],
            city=city,
            role=ser.validated_data.get('role', 'destination'),
        )
        return Response({'success': True, 'data': data})


class DriverBriefingAIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=DriverBriefingRequestSerializer,
        tags=['AI'],
        summary='Briefing corridor chauffeur',
        description='Recommandation de corridor, carrefours chauds et conseils pour la journée.',
    )
    def post(self, request):
        _require_driver(request.user)
        ser = DriverBriefingRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        city = ser.validated_data.get('city') or None
        data = driver_briefing(request.user, city=city)
        return Response({'success': True, 'data': data})


class ClassifySOSAIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ClassifySOSRequestSerializer,
        tags=['AI'],
        summary='Classifier une alerte SOS (texte)',
        description='Catégorie, urgence et actions recommandées avant dispatch secours.',
    )
    def post(self, request):
        ser = ClassifySOSRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = classify_sos(
            ser.validated_data.get('text', ''),
            emergency_type=ser.validated_data.get('emergency_type') or None,
            location=ser.validated_data.get('location'),
        )
        return Response({'success': True, 'data': data})
