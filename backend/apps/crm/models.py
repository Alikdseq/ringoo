"""
Модель заявки на отсутствующий товар (интеграция с CRM, задача 2.4.4).
"""

import uuid

from django.conf import settings
from django.db import models


class MissingProductRequest(models.Model):
    """Заявка на отсутствующий товар (отправка в CRM)."""

    STATUS_NEW = "new"
    STATUS_PROCESSED = "processed"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_NEW, "Новая"),
        (STATUS_PROCESSED, "В работе"),
        (STATUS_CLOSED, "Закрыта"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="missing_product_requests",
        verbose_name="Пользователь",
    )
    product_name = models.CharField(max_length=255, verbose_name="Название товара")
    contact_name = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Имя"
    )
    contact_phone = models.CharField(max_length=50, verbose_name="Телефон")
    contact_email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email",
    )
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
        verbose_name="Статус",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "crm_missingproductrequest"
        verbose_name = "Заявка на отсутствующий товар"
        verbose_name_plural = "Заявки на отсутствующий товар"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product_name} — {self.get_status_display()}"
