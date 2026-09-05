from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response

from geolocation.models import Zone
from geolocation.serializers import ZoneDetailSerializer, ZoneListSerializer


class ZoneListView(generics.ListAPIView):
    queryset = Zone.objects.filter(is_active=True).order_by('name')
    serializer_class = ZoneListSerializer

    @extend_schema(tags=['Zones'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ZoneDetailView(generics.RetrieveAPIView):
    queryset = Zone.objects.all()
    serializer_class = ZoneDetailSerializer

    @extend_schema(tags=['Zones'])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
