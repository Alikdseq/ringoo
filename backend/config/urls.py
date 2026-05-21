"""
URL configuration for Ringoo project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings

if getattr(settings, "ADMIN_OTP_ENABLED", False):
    from django_otp.admin import OTPAdminSite

    admin.site.__class__ = OTPAdminSite
from django.views.generic import RedirectView
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from config.views import health_check

urlpatterns = [
    path(settings.ADMIN_SITE_URL_PATH, admin.site.urls),
    # Health check
    path('health/', health_check, name='health'),
    # API v1
    path('api/v1/', include('config.api_urls')),
]

# Корень: при открытых docs (DEBUG или API_DOCS_PUBLIC) — на Swagger; иначе в prod — на /health/ (ниже).
_show_api_docs = getattr(settings, 'DEBUG', False) or getattr(
    settings, 'API_DOCS_PUBLIC', False
)
if _show_api_docs:
    urlpatterns = [
        path('', RedirectView.as_view(url='/api/docs/', permanent=False), name='root'),
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ] + urlpatterns
else:
    urlpatterns.insert(
        0,
        path('', RedirectView.as_view(url='/health/', permanent=False), name='root'),
    )

# Serve media files and Debug Toolbar in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Django Debug Toolbar — один префикс; дублирующий RedirectView на том же пути ломал панель.
    try:
        urlpatterns += [
            path('__debug__/', include('debug_toolbar.urls')),
        ]
    except Exception:
        pass
