from django.urls import path

from operations.views import AdminReportsView, AdminStatsView, AdminZoneListView, HealthView

urlpatterns = [
    path('health', HealthView.as_view(), name='health'),
    path('admin/zones', AdminZoneListView.as_view(), name='admin-zones'),
    path('admin/reports', AdminReportsView.as_view(), name='admin-reports'),
    path('admin/stats', AdminStatsView.as_view(), name='admin-stats'),
]
