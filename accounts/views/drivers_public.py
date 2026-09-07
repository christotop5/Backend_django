from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role, User
from geolocation.serializers import OnlineDriversResponseSerializer
from core.models import Vehicle


class OnlineDriversView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[OpenApiParameter('city', str, OpenApiParameter.QUERY, required=False)],
        responses={200: OnlineDriversResponseSerializer},
        tags=['Driver'],
    )
    def get(self, request):
        driver_role = Role.objects.filter(name='DRIVER').first()
        if not driver_role:
            return Response({'success': True, 'count': 0, 'data': []})

        qs = User.objects.filter(
            role=driver_role,
            is_active=True,
            profile__is_online=True,
        ).select_related('profile')
        city = request.query_params.get('city')
        if city:
            qs = qs.filter(profile__city__icontains=city)

        drivers = []
        for user in qs:
            profile = user.profile
            vehicle = Vehicle.objects.filter(assigned_driver=user).first()
            meta = profile.driver_metadata or {}
            drivers.append({
                'id': f'usr_{user.id}',
                'username': profile.username,
                'email': user.email,
                'full_name': f'{user.first_name} {user.last_name}'.strip(),
                'city': profile.city,
                'license_plate': vehicle.registration_number if vehicle else None,
                'car_model': vehicle.model if vehicle else None,
                'corridor_line': profile.corridor_axis,
                'available_seats': meta.get('available_seats', 4),
                'total_seats': meta.get('total_seats', 4),
                'rating': float(profile.rating),
                'status': meta.get('status', 'ONLINE' if profile.is_online else 'OFFLINE'),
                'location': {
                    'lat': float(profile.current_lat) if profile.current_lat else None,
                    'lng': float(profile.current_lng) if profile.current_lng else None,
                },
            })
        return Response({'success': True, 'count': len(drivers), 'data': drivers})
