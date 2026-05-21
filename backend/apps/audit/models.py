"""
Логирование действий в админке: кто и когда изменил товар / статус заказа.
"""

import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Запись о действии сотрудника в админке (изменение заказа, товара и т.д.)."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
        verbose_name="Пользователь",
    )
    action = models.CharField(max_length=64, verbose_name="Действие")
    model_name = models.CharField(max_length=128, verbose_name="Модель")
    object_id = models.CharField(max_length=64, blank=True, verbose_name="ID объекта")
    object_repr = models.CharField(max_length=255, blank=True, verbose_name="Объект")
    changes = models.JSONField(default=dict, blank=True, verbose_name="Изменения")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")

    class Meta:
        db_table = "audit_auditlog"
        verbose_name = "Запись аудита"
        verbose_name_plural = "Аудит действий"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.action} {self.model_name} {self.object_repr} by {self.user_id} at {self.created_at}"
