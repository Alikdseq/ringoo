"""Admin API: журнал и запуск синхронизации каталога 1С."""

from __future__ import annotations

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admin_api.permissions import RINGOO_GROUP_CATALOG, admin_permissions
from apps.products.sync_models import OneCCatalogSyncLog
from integrations.onec.catalog_sync import (
    has_running_apply,
    probe_connection,
    serialize_sync_log,
    sync_status_payload,
)


class OneCSyncStatusView(APIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def get(self, request):
        return Response(sync_status_payload())


class OneCSyncLogListView(APIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def get(self, request):
        qs = OneCCatalogSyncLog.objects.all().order_by("-created_at")[:50]
        return Response([serialize_sync_log(x) for x in qs])


class OneCSyncLogDetailView(APIView):
    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def get(self, request, pk):
        try:
            log = OneCCatalogSyncLog.objects.get(pk=pk)
        except OneCCatalogSyncLog.DoesNotExist:
            return Response({"detail": "Не найдено."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_sync_log(log))


class OneCSyncProbeView(APIView):
    """Проверка подключения (не меняет каталог)."""

    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def post(self, request):
        result = probe_connection(user=request.user)
        return Response(result)


class OneCSyncDryRunView(APIView):
    """Поставить dry-run в очередь Celery (или синхронно, если celery недоступен в tests)."""

    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def post(self, request):
        if not getattr(settings, "ONE_C_API_ENABLED", False):
            # Безопасный локальный dry-run на фикстурах без сети
            from pathlib import Path

            from integrations.onec.catalog_sync import run_catalog_import

            base = Path(__file__).resolve().parents[3] / "integrations" / "onec" / "fixtures"
            folders = base / "sample_folders.xml"
            products = base / "sample_products.xml"
            if folders.is_file() and products.is_file():
                data = run_catalog_import(
                    dry_run=True,
                    from_api=False,
                    user=request.user,
                    folders_path=str(folders),
                    products_path=str(products),
                )
                data["note"] = (
                    "ONE_C_API_ENABLED=false — выполнен dry-run по локальным fixtures"
                )
                return Response(data)
            return Response(
                {
                    "detail": "ONE_C_API_ENABLED=false и fixtures недоступны.",
                    "code": "onec_api_disabled",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        from apps.products.tasks import run_onec_catalog_sync_task

        async_result = run_onec_catalog_sync_task.delay(
            dry_run=True, user_id=str(request.user.pk)
        )
        return Response(
            {
                "queued": True,
                "celery_task_id": async_result.id,
                "dry_run": True,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class OneCSyncApplyView(APIView):
    """
    Постановка apply в очередь. Не вызывает live 1С, если API выключен.
    Требует confirm=true в теле.
    """

    permission_classes = admin_permissions(RINGOO_GROUP_CATALOG)

    def post(self, request):
        confirm = request.data.get("confirm")
        if confirm not in (True, "true", "1", 1, "yes"):
            return Response(
                {
                    "detail": "Подтвердите apply: передайте confirm=true.",
                    "code": "confirm_required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not getattr(settings, "ONE_C_API_ENABLED", False):
            return Response(
                {
                    "detail": (
                        "Apply запрещён: ONE_C_API_ENABLED=false. "
                        "Включите только на согласованном контуре 1С."
                    ),
                    "code": "onec_api_disabled",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if has_running_apply():
            return Response(
                {
                    "detail": "Apply уже выполняется.",
                    "code": "sync_already_running",
                },
                status=status.HTTP_409_CONFLICT,
            )

        from apps.products.tasks import run_onec_catalog_sync_task

        async_result = run_onec_catalog_sync_task.delay(
            dry_run=False, user_id=str(request.user.pk)
        )
        return Response(
            {
                "queued": True,
                "celery_task_id": async_result.id,
                "dry_run": False,
                "warning": (
                    "Задача поставлена в очередь. Успех = завершённый SyncLog, "
                    "не факт принятия Celery."
                ),
            },
            status=status.HTTP_202_ACCEPTED,
        )
