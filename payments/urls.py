from django.urls import path

from payments.views import (
    CashConfirmView,
    MTNMomoPaymentView,
    MTNWebhookView,
    OrangeMoneyPaymentView,
    OrangeWebhookView,
    PaymentStatusView,
)

urlpatterns = [
    path('payments/mtn-momo', MTNMomoPaymentView.as_view(), name='payments-mtn-momo'),
    path('payments/orange-money', OrangeMoneyPaymentView.as_view(), name='payments-orange-money'),
    path('payments/cash/confirm', CashConfirmView.as_view(), name='payments-cash-confirm'),
    path('payments/<str:transaction_id>/status', PaymentStatusView.as_view(), name='payments-status'),
    path('webhooks/mtn-momo', MTNWebhookView.as_view(), name='webhooks-mtn-momo'),
    path('webhooks/orange-money', OrangeWebhookView.as_view(), name='webhooks-orange-money'),
]
