"""Admin API: создание / статус / скачивание резервных копий."""

from __future__ import annotations

import logging

from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admin_api.permissions import AdminMfaVerified, IsStaff
from apps.backups.models import BackupArchive
from apps.backups.services import (
    create_backup_archive,
    resolve_archive_path,
    verify_download_token,
)

logger = logging.getLogger(__name__)


class IsSuperuserBackupAdmin(BasePermission):
    """Только суперпользователь — полный доступ к PII в дампе."""

    message = "Резервное копирование доступно только суперпользователю."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_staff
            and user.is_superuser
        )


BACKUP_PERMISSIONS = [
    IsAuthenticated,
    IsStaff,
    AdminMfaVerified,
    IsSuperuserBackupAdmin,
]


def _audit(request, action: str, **extra):
    logger.info(
        "backup_audit action=%s user_id=%s ip=%s extra=%s",
        action,
        getattr(request.user, "pk", None),
        request.META.get("REMOTE_ADDR"),
        {k: v for k, v in extra.items() if k not in ("password", "token")},
    )


class BackupCreateView(APIView):
    permission_classes = BACKUP_PERMISSIONS

    def post(self, request):
        password = request.data.get("password") or None
        if password is not None:
            password = str(password)
            if len(password) < 8:
                return Response(
                    {"detail": "Пароль шифрования должен быть не короче 8 символов."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if len(password) > 128:
                return Response(
                    {"detail": "Слишком длинный пароль."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        try:
            archive, token = create_backup_archive(
                user=request.user, password=password
            )
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except Exception as exc:
            _audit(request, "create_failed", error=str(exc)[:200])
            return Response(
                {"detail": "Не удалось создать резервную копию."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        _audit(
            request,
            "create_ok",
            archive_id=str(archive.pk),
            encrypted=archive.encrypted,
            size=archive.size_bytes,
        )
        return Response(
            {
                "id": str(archive.pk),
                "status": archive.status,
                "filename": archive.filename,
                "size_bytes": archive.size_bytes,
                "sha256": archive.sha256,
                "encrypted": archive.encrypted,
                "expires_at": archive.expires_at,
                "download_token": token,
                "manifest": archive.manifest,
            },
            status=status.HTTP_201_CREATED,
        )


class BackupStatusView(APIView):
    permission_classes = BACKUP_PERMISSIONS

    def get(self, request, backup_id):
        try:
            archive = BackupArchive.objects.get(pk=backup_id)
        except BackupArchive.DoesNotExist:
            return Response({"detail": "Не найдено."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "id": str(archive.pk),
                "status": archive.status,
                "filename": archive.filename,
                "size_bytes": archive.size_bytes,
                "sha256": archive.sha256,
                "encrypted": archive.encrypted,
                "expires_at": archive.expires_at,
                "error_message": archive.error_message,
                "manifest": archive.manifest,
                "downloadable": archive.is_downloadable,
            }
        )


class BackupDownloadView(APIView):
    permission_classes = BACKUP_PERMISSIONS

    def get(self, request, backup_id):
        token = request.query_params.get("token") or ""
        try:
            archive = BackupArchive.objects.get(pk=backup_id)
        except BackupArchive.DoesNotExist:
            return Response({"detail": "Не найдено."}, status=status.HTTP_404_NOT_FOUND)
        if not archive.is_downloadable:
            return Response(
                {"detail": "Архив недоступен или срок истёк."},
                status=status.HTTP_410_GONE,
            )
        if not verify_download_token(archive, token):
            _audit(request, "download_denied", archive_id=str(archive.pk))
            return Response({"detail": "Неверный токен."}, status=status.HTTP_403_FORBIDDEN)
        path = resolve_archive_path(archive)
        if path is None:
            return Response(
                {"detail": "Файл не найден."}, status=status.HTTP_404_NOT_FOUND
            )
        archive.downloaded_at = timezone.now()
        archive.save(update_fields=["downloaded_at", "updated_at"])
        _audit(
            request,
            "download_ok",
            archive_id=str(archive.pk),
            size=archive.size_bytes,
        )
        return FileResponse(
            path.open("rb"),
            as_attachment=True,
            filename=archive.filename or "ringoo_backup.zip",
        )


class BackupLatestView(APIView):
    permission_classes = BACKUP_PERMISSIONS

    def get(self, request):
        archive = BackupArchive.objects.order_by("-created_at").first()
        if not archive:
            return Response({"detail": "Нет архивов."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "id": str(archive.pk),
                "status": archive.status,
                "filename": archive.filename,
                "size_bytes": archive.size_bytes,
                "encrypted": archive.encrypted,
                "expires_at": archive.expires_at,
                "created_at": archive.created_at,
                "downloadable": archive.is_downloadable,
                "offsite_status": archive.offsite_status,
            }
        )


class BackupOffsiteStatusView(APIView):
    permission_classes = BACKUP_PERMISSIONS

    def get(self, request):
        from apps.backups.crypto_keys import key_inventory_public
        from apps.backups.offsite import offsite_status_snapshot

        snap = offsite_status_snapshot()
        snap["encryption"] = key_inventory_public()
        return Response(snap)


class BackupOffsiteProbeView(APIView):
    permission_classes = BACKUP_PERMISSIONS

    def post(self, request):
        from apps.backups.s3 import probe_connection

        _audit(request, "offsite_probe")
        return Response(probe_connection())


class BackupOffsiteUploadView(APIView):
    """Поставить загрузку архива во внешнее хранилище в очередь Celery."""

    permission_classes = BACKUP_PERMISSIONS

    def post(self, request, backup_id=None):
        from apps.backups.tasks import create_and_upload_offsite_backup_task

        archive_id = backup_id or request.data.get("archive_id")
        if archive_id:
            try:
                BackupArchive.objects.get(pk=archive_id)
            except BackupArchive.DoesNotExist:
                return Response({"detail": "Не найдено."}, status=status.HTTP_404_NOT_FOUND)
        _audit(request, "offsite_upload_enqueue", archive_id=str(archive_id or ""))
        async_result = create_and_upload_offsite_backup_task.delay(
            str(archive_id) if archive_id else None
        )
        return Response(
            {"status": "RUNNING", "task_id": getattr(async_result, "id", None)},
            status=status.HTTP_202_ACCEPTED,
        )


class BackupOffsiteVerifyView(APIView):
    permission_classes = BACKUP_PERMISSIONS

    def post(self, request):
        from apps.backups.offsite import verify_latest_offsite

        _audit(request, "offsite_verify")
        try:
            result = verify_latest_offsite()
        except Exception as exc:
            return Response(
                {"status": "FAILED", "detail": str(exc)[:200]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        code = (
            status.HTTP_200_OK
            if result.get("status") == "SUCCESS"
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(result, status=code)
