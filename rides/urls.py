from django.urls import path

from rides.views import RideEstimateView, RidePayView, RideRateView, RideRequestView, RideStatusView
from rides.views.driver_rides import (
    DriverActiveRidesView,
    DriverApproveRideView,
    DriverCompleteRideView,
    DriverPendingRidesView,
    DriverRejectRideView,
    DriverRideMapView,
)
from rides.views.map_views import NearbyDriversView, NearestCarrefourView
from rides.views.passenger_lifecycle import PassengerArrivedView, PassengerBoardView, RideMapView

urlpatterns = [
    path('geo/nearest-carrefour', NearestCarrefourView.as_view(), name='geo-nearest-carrefour'),
    path('rides/nearby-drivers', NearbyDriversView.as_view(), name='rides-nearby-drivers'),
    path('rides/estimate', RideEstimateView.as_view(), name='rides-estimate'),
    path('rides/request', RideRequestView.as_view(), name='rides-request'),
    path('rides/<str:ride_id>/status', RideStatusView.as_view(), name='rides-status'),
    path('rides/<str:ride_id>/map', RideMapView.as_view(), name='rides-map'),
    path('rides/<str:ride_id>/passenger-arrived', PassengerArrivedView.as_view(), name='rides-passenger-arrived'),
    path('rides/<str:ride_id>/board', PassengerBoardView.as_view(), name='rides-board'),
    path('rides/<str:ride_id>/payment', RidePayView.as_view(), name='rides-payment'),
    path('rides/<str:ride_id>/rate', RideRateView.as_view(), name='rides-rate'),
    path('driver/rides/pending', DriverPendingRidesView.as_view(), name='driver-rides-pending'),
    path('driver/rides/active', DriverActiveRidesView.as_view(), name='driver-rides-active'),
    path('driver/rides/<str:ride_id>/map', DriverRideMapView.as_view(), name='driver-ride-map'),
    path('driver/rides/<str:ride_id>/approve', DriverApproveRideView.as_view(), name='driver-ride-approve'),
    path('driver/rides/<str:ride_id>/reject', DriverRejectRideView.as_view(), name='driver-ride-reject'),
    path('driver/rides/<str:ride_id>/complete', DriverCompleteRideView.as_view(), name='driver-ride-complete'),
]
