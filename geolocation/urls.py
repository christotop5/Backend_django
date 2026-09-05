from django.urls import path

from geolocation.views.carrefours import CarrefourListCreateView
from geolocation.views.geo import CongestionView, GeocodeView, ReverseGeocodeView, RouteView
from geolocation.views.trajectories import (
    TrajectoryActiveView,
    TrajectoryDetailView,
    TrajectoryListCreateView,
)
from geolocation.views.zones import ZoneDetailView, ZoneListView

urlpatterns = [
    path('geo/geocode', GeocodeView.as_view(), name='geo-geocode'),
    path('geo/reverse-geocode', ReverseGeocodeView.as_view(), name='geo-reverse-geocode'),
    path('geo/route', RouteView.as_view(), name='geo-route'),
    path('geo/congestion', CongestionView.as_view(), name='geo-congestion'),
    path('zones', ZoneListView.as_view(), name='zone-list'),
    path('zones/<int:pk>', ZoneDetailView.as_view(), name='zone-detail'),
    path('carrefours', CarrefourListCreateView.as_view(), name='carrefour-list-create'),
    path('drivers/<int:driver_id>/trajectories', TrajectoryListCreateView.as_view(), name='trajectory-list-create'),
    path('drivers/<int:driver_id>/trajectories/active', TrajectoryActiveView.as_view(), name='trajectory-active'),
    path('drivers/<int:driver_id>/trajectories/<int:trajectory_id>', TrajectoryDetailView.as_view(), name='trajectory-detail'),
]
