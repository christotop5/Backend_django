from django.urls import path

from accounts.views.auth import MeView, OTPSendView, OTPVerifyView, SigninView, SignupView
from accounts.views.driver import (
    DriverCabinSeatView,
    DriverCorridorView,
    DriverStatusView,
    DriverWithdrawView,
)
from accounts.views.drivers_public import OnlineDriversView

urlpatterns = [
    path('auth/signup', SignupView.as_view(), name='auth-signup'),
    path('auth/otp/send', OTPSendView.as_view(), name='auth-otp-send'),
    path('auth/otp/verify', OTPVerifyView.as_view(), name='auth-otp-verify'),
    path('auth/signin', SigninView.as_view(), name='auth-signin'),
    path('auth/me', MeView.as_view(), name='auth-me'),
    path('drivers/online', OnlineDriversView.as_view(), name='drivers-online'),
    path('driver/status', DriverStatusView.as_view(), name='driver-status'),
    path('driver/corridor', DriverCorridorView.as_view(), name='driver-corridor'),
    path('driver/cabin-seats/<int:seat_id>', DriverCabinSeatView.as_view(), name='driver-cabin-seat'),
    path('driver/withdraw', DriverWithdrawView.as_view(), name='driver-withdraw'),
]
