from django.urls import path

from optimization.views import DemandHeatmapView, OptimizeTurnView, VerifyDestinationView

urlpatterns = [
    path('optimize/turn', OptimizeTurnView.as_view(), name='optimize-turn'),
    path('geo/verify-destination', VerifyDestinationView.as_view(), name='verify-destination'),
    path('optimize/demand-heatmap', DemandHeatmapView.as_view(), name='demand-heatmap'),
]
