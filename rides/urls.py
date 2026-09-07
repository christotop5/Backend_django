from django.urls import path

from rides.views import RideEstimateView, RidePayView, RideRateView, RideRequestView, RideStatusView

urlpatterns = [
    path('rides/estimate', RideEstimateView.as_view(), name='rides-estimate'),
    path('rides/request', RideRequestView.as_view(), name='rides-request'),
    path('rides/<str:ride_id>/status', RideStatusView.as_view(), name='rides-status'),
    path('rides/<str:ride_id>/payment', RidePayView.as_view(), name='rides-payment'),
    path('rides/<str:ride_id>/rate', RideRateView.as_view(), name='rides-rate'),
]
