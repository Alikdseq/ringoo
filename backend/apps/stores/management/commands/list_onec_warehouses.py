"""
Список магазинов и полей 1С; опционально применить mapping JSON.

Примеры:
  python manage.py list_onec_warehouses
  python manage.py list_onec_warehouses --apply path/to/mapping.json --dry-run
  python manage.py list_onec_warehouses --apply mapping.json

Формат mapping.json:
[
  {"slug": "apple-room", "onec_warehouse_id": "...", "onec_warehouse_name": "Apple Room", "is_warehouse": true},
  {"slug": "store-center", "onec_warehouse_id": "...", "is_warehouse": false}
]
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.stores.models import Store


class Command(BaseCommand):
    help = "Показать/заполнить onec_warehouse_id и is_warehouse у магазинов."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            type=str,
            default="",
            help="Путь к JSON-маппингу (slug → onec fields).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать изменения, не сохранять.",
        )

    def handle(self, *args, **options):
        apply_path = (options.get("apply") or "").strip()
        dry_run = bool(options.get("dry_run"))

        if apply_path:
            self._apply_mapping(Path(apply_path), dry_run=dry_run)
        else:
            self._list_stores()

    def _list_stores(self):
        qs = Store.objects.all().order_by("city", "name")
        if not qs.exists():
            self.stdout.write("Магазинов в БД нет.")
            return
        missing = 0
        for s in qs:
            oid = (s.onec_warehouse_id or "").strip()
            if not oid:
                missing += 1
            self.stdout.write(
                f"{s.slug}\tactive={s.is_active}\twh={s.is_warehouse}\t"
                f"oid={oid or '-'}\toname={s.onec_warehouse_name or '-'}\t{s.name}"
            )
        self.stdout.write(
            self.style.WARNING(f"Всего: {qs.count()}, без onec_warehouse_id: {missing}")
        )
        self.stdout.write(
            "Заполните ID через Django Admin /admin FE, либо --apply mapping.json"
        )

    def _apply_mapping(self, path: Path, *, dry_run: bool):
        if not path.is_file():
            raise CommandError(f"Файл не найден: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Некорректный JSON: {exc}") from exc
        if not isinstance(data, list):
            raise CommandError("Ожидается JSON-массив объектов.")

        updated = 0
        for row in data:
            if not isinstance(row, dict) or not row.get("slug"):
                raise CommandError(f"Каждая запись должна иметь slug: {row!r}")
            slug = str(row["slug"]).strip()
            try:
                store = Store.objects.get(slug=slug)
            except Store.DoesNotExist as exc:
                raise CommandError(f"Магазин slug={slug!r} не найден") from exc

            dirty: list[str] = []
            if "onec_warehouse_id" in row:
                val = (row.get("onec_warehouse_id") or "").strip() or None
                if store.onec_warehouse_id != val:
                    store.onec_warehouse_id = val
                    dirty.append("onec_warehouse_id")
            if "onec_warehouse_name" in row:
                val = (row.get("onec_warehouse_name") or "").strip() or None
                if store.onec_warehouse_name != val:
                    store.onec_warehouse_name = val
                    dirty.append("onec_warehouse_name")
            if "is_warehouse" in row:
                flag = bool(row["is_warehouse"])
                if store.is_warehouse != flag:
                    store.is_warehouse = flag
                    dirty.append("is_warehouse")
            if "is_active" in row:
                flag = bool(row["is_active"])
                if store.is_active != flag:
                    store.is_active = flag
                    dirty.append("is_active")

            if not dirty:
                self.stdout.write(f"skip {slug}: без изменений")
                continue
            self.stdout.write(f"{'DRY ' if dry_run else ''}update {slug}: {', '.join(dirty)}")
            if not dry_run:
                store.save(update_fields=[*dirty, "updated_at"])
            updated += 1

        msg = f"Готово: {updated} магазинов{' (dry-run)' if dry_run else ''}."
        self.stdout.write(self.style.SUCCESS(msg))
