from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from operations.views.safety import SOSView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/v1/docs/',
        SpectacularSwaggerView.as_view(
            url_name='schema',
            title='VORA Platform API — Documentation',
        ),
        name='swagger-ui',
    ),
    path('api/v1/', include('accounts.urls')),
    path('api/v1/', include('rides.urls')),
    path('api/v1/', include('payments.urls')),
    path('api/v1/safety/sos', SOSView.as_view(), name='safety-sos'),
    path('api/v1/', include('operations.urls')),
    path('api/v1/', include('geolocation.urls')),
    path('api/v1/', include('optimization.urls')),
    path('api/v1/', include('ai.urls')),
]
