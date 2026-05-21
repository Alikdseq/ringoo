"""
API заявок на отсутствующий товар (CRM, задача 2.4.4).
"""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.throttling import CrmCreateAnonThrottle

from .models import MissingProductRequest
from .serializers import MissingProductRequestCreateSerializer
from .tasks import send_missing_product_request_to_crm


class MissingProductRequestCreateView(APIView):
    """POST: создание заявки на отсутствующий товар (доступно без авторизации)."""

    permission_classes = [AllowAny]
    throttle_classes = [CrmCreateAnonThrottle]
    serializer_class = MissingProductRequestCreateSerializer

    def post(self, request):
        serializer = MissingProductRequestCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        send_missing_product_request_to_crm.delay(str(instance.id))
        return Response(serializer.data, status=status.HTTP_201_CREATED)
