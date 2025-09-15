from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectSessionViewSet, LayerViewSet, ProcessingViewSet, 
    MapViewSet, QRViewSet, HealthCheckViewSet
)

router = DefaultRouter()
router.register(r'projects', ProjectSessionViewSet, basename='project')
router.register(r'layers', LayerViewSet, basename='layer')
router.register(r'processing', ProcessingViewSet, basename='processing')
router.register(r'map', MapViewSet, basename='map')
router.register(r'qr', QRViewSet, basename='qr')
router.register(r'health', HealthCheckViewSet, basename='health')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/', include(router.urls)),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)