"""
Юридические endpoint'ы (согласие на аналитику cookie).
"""

from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.throttling import LegalAnalyticsAnonThrottle

from .consent import record_consent
from .models import ConsentRecord


class AnalyticsConsentSerializer(serializers.Serializer):
    consent = serializers.BooleanField(required=True)


class AnalyticsConsentView(APIView):
    """POST: фиксация согласия на cookie аналитики (Яндекс.Метрика)."""

    permission_classes = [AllowAny]
    throttle_classes = [LegalAnalyticsAnonThrottle]

    def post(self, request):
        serializer = AnalyticsConsentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["consent"]:
            user = request.user if request.user.is_authenticated else None
            record_consent(request, ConsentRecord.TYPE_ANALYTICS, user=user)
        return Response({"detail": "ok"}, status=status.HTTP_200_OK)
