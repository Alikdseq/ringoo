"""
Проверка папок frontend/public/{Samsung,Iphone,...}: группировка фото по цветам из имён файлов.
Запуск: python manage.py audit_public_catalog_colors
После правок в public — переимпорт: python manage.py import_public_catalog
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.products.services.public_catalog_flat import group_flat_images_by_color
from apps.products.services.public_catalog_iter import (
    iter_model_directories,
    list_images,
    list_subdirs,
)

BRAND_DIRS = ("Samsung", "Iphone", "Xiaomi", "Tecno", "Infinix", "Huawei", "Realme")


class Command(BaseCommand):
    help = "Аудит соответствия файлов и цветов в public-каталоге"

    def handle(self, *args, **options):
        root = Path(getattr(settings, "RINGOO_PUBLIC_CATALOG_ROOT", ""))
        if not root.is_dir():
            self.stderr.write(self.style.ERROR(f"Нет каталога: {root}"))
            return

        issues = 0
        models_checked = 0
        for brand in BRAND_DIRS:
            brand_dir = root / brand
            if not brand_dir.is_dir():
                continue
            self.stdout.write(self.style.MIGRATE_HEADING(brand))
            for model_dir, title in iter_model_directories(brand_dir):
                subdirs = list_subdirs(model_dir)
                root_images = list_images(model_dir)
                if subdirs:
                    for sd in subdirs:
                        imgs = list_images(sd)
                        if imgs:
                            rel = model_dir.relative_to(root)
                            self.stdout.write(
                                f"  {rel}/{sd.name}: {len(imgs)} файлов (папка-цвет)"
                            )
                    continue
                if len(root_images) < 2:
                    continue

                models_checked += 1
                groups = group_flat_images_by_color(root_images)
                rel = model_dir.relative_to(root)
                if not groups:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  {rel} ({title}): {len(root_images)} файлов — "
                            "не удалось выделить цвета по именам"
                        )
                    )
                    issues += 1
                elif len(groups) == 1:
                    key = next(iter(groups))
                    self.stdout.write(
                        f"  {rel}: OK — 1 цвет ({key}), {len(root_images)} файлов"
                    )
                else:
                    keys = ", ".join(sorted(groups.keys()))
                    self.stdout.write(
                        f"  {rel}: OK — {len(groups)} цветов ({keys})"
                    )

        self.stdout.write(f"Плоских моделей проверено: {models_checked}")
        if issues:
            self.stdout.write(self.style.WARNING(f"Моделей с замечаниями: {issues}"))
        else:
            self.stdout.write(self.style.SUCCESS("Группировка по именам файлов выглядит корректно."))
        self.stdout.write("Для обновления БД: python manage.py import_public_catalog")
