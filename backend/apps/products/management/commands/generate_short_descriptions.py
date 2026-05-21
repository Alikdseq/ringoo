"""
Заполнение short_description (и при пустом description — краткий абзац) для товаров без текста.

Использование:
  python manage.py generate_short_descriptions --dry-run
  python manage.py generate_short_descriptions
  python manage.py generate_short_descriptions --force
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.products.models import Product
from apps.products.utils import iphone_product_model_tail


def _load_templates() -> dict:
    path = Path(__file__).resolve().parent.parent.parent / "data" / "description_templates.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _category_kind(category_slug: str | None, title: str) -> str:
    s = (category_slug or "").lower()
    t = title.lower()
    if s in {"iphone", "samsung", "smartphones"} or "смартфон" in t:
        return "smartphone"
    if s in {"headphones", "audio"} or "наушник" in t:
        return "headphones"
    if s in {"accessories", "cases", "glass"} or "чехол" in t or "стекл" in t:
        return "accessory"
    return "generic"


def _generic_text(kind: str, product: Product, templates: dict) -> str:
    brand = (product.brand or "").strip()
    if brand and brand in templates.get("by_brand", {}):
        base = templates["by_brand"][brand]
    else:
        cat_slug = product.category.slug if product.category_id else ""
        base = templates.get("by_category_slug", {}).get(
            cat_slug, templates.get("default", "")
        )

    title = product.title or "Товар"
    sku = product.sku or ""
    if kind == "smartphone":
        extra = f" Модель: {title}."
        if sku:
            extra += f" Артикул: {sku}."
        return (base + extra).strip()
    if kind == "accessory":
        return f"{base} Подходит для: {title}." + (f" SKU: {sku}." if sku else "")
    if kind == "headphones":
        return f"{base} {title}." + (f" Артикул: {sku}." if sku else "")
    return f"{base} {title}."


def _curated_for_slug(slug: str, templates: dict) -> str | None:
    by_slug = templates.get("by_slug", {})
    if slug in by_slug:
        return by_slug[slug]
    tail = iphone_product_model_tail(slug)
    if tail:
        for key, text in by_slug.items():
            if key.endswith(tail) or tail in key:
                return text
    return None


class Command(BaseCommand):
    help = "Генерирует short_description для товаров с пустым кратким описанием."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать, что будет обновлено, без записи в БД.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Перезаписать существующие short_description.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        force: bool = options["force"]
        templates = _load_templates()

        qs = Product.objects.select_related("category").all()
        if not force:
            qs = qs.filter(Q(short_description__isnull=True) | Q(short_description=""))

        updated = 0
        skipped = 0

        for product in qs.iterator(chunk_size=200):
            curated = _curated_for_slug(product.slug, templates)
            if curated:
                text = curated
            else:
                kind = _category_kind(
                    product.category.slug if product.category_id else None,
                    product.title or "",
                )
                text = _generic_text(kind, product, templates)

            if not text:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"Skip (no text): {product.slug}"))
                continue

            needs_desc = not (product.description or "").strip()
            if dry_run:
                self.stdout.write(f"[dry-run] {product.slug}: {text[:80]}...")
                updated += 1
                continue

            product.short_description = text[:500]
            if needs_desc:
                product.description = f"<p>{text}</p>"
            product.save(update_fields=["short_description", "description"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Updated: {updated}, skipped: {skipped}, dry_run={dry_run}, force={force}"
            )
        )
