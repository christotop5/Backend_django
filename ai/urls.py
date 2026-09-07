from django.urls import path

from ai.views import (
    ChatAIView,
    ClassifySOSAIView,
    DriverBriefingAIView,
    ParseRideAIView,
    ResolveDestinationAIView,
)

urlpatterns = [
    path('ai/parse-ride', ParseRideAIView.as_view(), name='ai-parse-ride'),
    path('ai/chat', ChatAIView.as_view(), name='ai-chat'),
    path('ai/resolve-destination', ResolveDestinationAIView.as_view(), name='ai-resolve-destination'),
    path('ai/driver-briefing', DriverBriefingAIView.as_view(), name='ai-driver-briefing'),
    path('ai/classify-sos', ClassifySOSAIView.as_view(), name='ai-classify-sos'),
]
