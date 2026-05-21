"""
Маршруты аутентификации и текущего пользователя.
"""

from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .views import (
    CookieTokenRefreshView,
    DeleteAccountView,
    DeliveryAddressDetailView,
    DeliveryAddressListCreateView,
    LogoutView,
    RegisterView,
    StaffAccessView,
    TokenObtainPairViewNoCSRF,
    UserDataExportView,
    UserMeView,
)

app_name = "users"

urlpatterns = [
    path("me/", UserMeView.as_view(), name="auth-me"),
    path("me/export/", UserDataExportView.as_view(), name="auth-me-export"),
    path("staff-access/", StaffAccessView.as_view(), name="auth-staff-access"),
    path("delete-account/", DeleteAccountView.as_view(), name="delete-account"),
    path("token/", csrf_exempt(TokenObtainPairViewNoCSRF.as_view()), name="token_obtain_pair"),
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path("addresses/", DeliveryAddressListCreateView.as_view(), name="address-list-create"),
    path("addresses/<int:pk>/", DeliveryAddressDetailView.as_view(), name="address-detail"),
]
