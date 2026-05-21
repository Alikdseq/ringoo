"""
Админка заявок на отсутствующий товар.
"""

from django.contrib import admin
from .models import MissingProductRequest


@admin.register(MissingProductRequest)
class MissingProductRequestAdmin(admin.ModelAdmin):
    list_display = ("product_name", "contact_name", "contact_phone", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("product_name", "contact_name", "contact_phone", "contact_email")
    readonly_fields = ("id", "created_at")
