"""
Импорт товаров из frontend/public: папки брендов → категории, подпапки → модели.
Фото: подпапки по цвету, colors.json, или авто-группировка по имени файла.
Все изображения → WebP на белом фоне в MEDIA.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.products.models import Category, Product, ProductColor, ProductImage
from apps.products.services.image_pipeline import bytes_to_webp_on_white
from apps.products.services.public_catalog_flat import (
    canonical_color_slug,
    group_flat_images_by_color,
    guess_hex_for_slug,
    label_from_color_slug,
)
from apps.products.services.public_catalog_iter import (
    _subdir_looks_like_color_folder,
    iter_model_directories,
    list_images,
    list_subdirs,
    model_slug_from_path,
)
from apps.stores.models import Stock, Store

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

# (имена папок в public, slug категории, title категории, sort_order, Product.brand)
BRAND_CATALOG: tuple[tuple[tuple[str, ...], str, str, int, str], ...] = (
    (("Iphone", "iphone", "iphones", "apple"), "iphone", "iPhone", 0, "Apple"),
    (("Samsung", "samsung"), "samsung", "Samsung", 1, "Samsung"),
    (("Huawei", "huawei"), "huawei", "Huawei", 2, "Huawei"),
    (("Xiaomi", "xiaomi"), "xiaomi", "Xiaomi", 3, "Xiaomi"),
    (("Realme", "realme"), "realme", "Realme", 4, "Realme"),
    (("Tecno", "tecno"), "tecno", "Tecno", 5, "Tecno"),
    (("Infinix", "infinix"), "infinix", "Infinix", 6, "Infinix"),
)

BRAND_DISPLAY_BY_SLUG: dict[str, str] = {row[1]: row[4] for row in BRAND_CATALOG}


class Command(BaseCommand):
    help = (
        "Импорт каталога из RINGOO_PUBLIC_CATALOG_ROOT: папки брендов в public, "
        "рекурсивно — модели с фото; категория = slug бренда."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--root",
            type=str,
            default="",
            help="Корень public (иначе settings.RINGOO_PUBLIC_CATALOG_ROOT)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только вывод действий без записи в БД",
        )
        parser.add_argument(
            "--brand",
            type=str,
            default="",
            help="Импорт только одного slug категории (iphone, samsung, huawei, …)",
        )

    def handle(self, *args, **options):
        root = Path(options["root"] or getattr(settings, "RINGOO_PUBLIC_CATALOG_ROOT", ""))
        dry = options["dry_run"]
        only_brand = (options["brand"] or "").strip().lower()

        if not root.is_dir():
            self.stderr.write(self.style.ERROR(f"Каталог не найден: {root}"))
            return

        categories = self._ensure_categories(dry)

        found_any = False
        for folder_names, cat_slug, cat_title, _sort, _brand_display in BRAND_CATALOG:
            if only_brand and cat_slug != only_brand:
                continue
            brand_dir: Path | None = None
            for fname in folder_names:
                p = root / fname
                if p.is_dir():
                    brand_dir = p
                    break
            if brand_dir is None:
                continue

            found_any = True
            category = categories.get(cat_slug) if categories else None
            self.stdout.write(self.style.MIGRATE_HEADING(f"Бренд {cat_title} ({brand_dir.name})"))
            for model_dir, title in iter_model_directories(brand_dir):
                product_slug = model_slug_from_path(model_dir, brand_dir, cat_slug)
                self._import_model(
                    model_dir=model_dir,
                    category=category,
                    category_slug=cat_slug,
                    product_slug=product_slug,
                    title=title,
                    dry=dry,
                )

        if not found_any:
            self.stdout.write(self.style.WARNING("Нет папок брендов для импорта."))
        elif not dry:
            from apps.products.cache_utils import bump_products_list_version

            bump_products_list_version()
            self.stdout.write(self.style.SUCCESS("Кэш списка товаров сброшен."))

    def _ensure_categories(self, dry: bool) -> dict[str, Category] | None:
        if dry:
            return None

        out: dict[str, Category] = {}
        slugs: list[str] = []
        for _folders, cat_slug, cat_title, sort_order, _brand in BRAND_CATALOG:
            cat, _ = Category.objects.get_or_create(
                slug=cat_slug,
                defaults={
                    "title": cat_title,
                    "is_active": True,
                    "sort_order": sort_order,
                },
            )
            Category.objects.filter(pk=cat.pk).update(
                title=cat_title,
                is_active=True,
                sort_order=sort_order,
            )
            out[cat_slug] = cat
            slugs.append(cat_slug)

        Category.objects.filter(slug__in=slugs).update(is_active=True)
        return out

    def _import_model(
        self,
        *,
        model_dir: Path,
        category: Category | None,
        category_slug: str,
        product_slug: str,
        title: str,
        dry: bool,
    ):
        model_slug_tail = product_slug.removeprefix(f"{category_slug}-") or product_slug
        self.stdout.write(f"- {title} -> {product_slug} ({category_slug})")

        colors_path = model_dir / "colors.json"
        color_defs: list[dict] = []
        if colors_path.is_file():
            try:
                color_defs = json.loads(colors_path.read_text(encoding="utf-8"))
                if not isinstance(color_defs, list):
                    color_defs = []
            except json.JSONDecodeError as e:
                self.stderr.write(self.style.WARNING(f"  colors.json: {e}"))

        json_by_slug: dict[str, dict] = {}
        for c in color_defs:
            if not isinstance(c, dict):
                continue
            cs_raw = slugify(str(c.get("slug", "")))
            if not cs_raw:
                continue
            cs = canonical_color_slug(cs_raw)
            prev = json_by_slug.get(cs)
            if prev is None:
                json_by_slug[cs] = c
            else:
                lab_new = str(c.get("label") or "")
                lab_old = str(prev.get("label") or "")
                if "cam" in lab_old.lower() and "cam" not in lab_new.lower():
                    json_by_slug[cs] = c
                elif "cam" in lab_new.lower() and "cam" not in lab_old.lower():
                    pass
                else:
                    json_by_slug[cs] = c

        subdirs = list_subdirs(model_dir)
        root_images = list_images(model_dir)

        color_folder_files: dict[str, list[Path]] = defaultdict(list)
        for sd in subdirs:
            if not _subdir_looks_like_color_folder(sd):
                continue
            imgs = list_images(sd)
            if imgs:
                raw = slugify(sd.name) or sd.name.lower()
                cs = canonical_color_slug(raw)
                color_folder_files[cs].extend(imgs)

        for cs in list(color_folder_files.keys()):
            color_folder_files[cs] = sorted(
                {p.resolve(): p for p in color_folder_files[cs]}.values(),
                key=lambda p: p.name.lower(),
            )

        flat_groups: dict[str, list[Path]] = {}
        if not color_folder_files and root_images:
            flat_groups = group_flat_images_by_color(root_images)

        if dry:
            self.stdout.write(
                f"  [dry-run] slug={product_slug}, папки-цвета={len(color_folder_files)}, "
                f"плоских групп={len(flat_groups)}, файлов в корне={len(root_images)}, "
                f"colors.json={len(color_defs)}"
            )
            return

        if category is None:
            return

        brand_display = BRAND_DISPLAY_BY_SLUG.get(category_slug, category_slug.title())

        with transaction.atomic():
            product, _ = Product.objects.update_or_create(
                slug=product_slug,
                defaults={
                    "title": title[:255],
                    "category": category,
                    "brand": brand_display,
                    "price": Decimal("99900.00"),
                    "description": "",
                    "short_description": "",
                    "is_active": True,
                    "sku": (product_slug.replace("-", "_"))[:100].upper(),
                    "rating": 4.7,
                    "reviews_count": 0,
                },
            )
            product.images.all().delete()
            product.colors.all().delete()

            color_by_slug: dict[str, ProductColor] = {}
            order = 0

            def upsert_color(cs: str, fallback_label: str) -> ProductColor:
                nonlocal order
                if cs in color_by_slug:
                    return color_by_slug[cs]
                meta = json_by_slug.get(cs, {})
                lab = str(meta.get("label") or fallback_label)[:255]
                if re.search(r"\bcam\b", lab, re.I):
                    lab = label_from_color_slug(cs)[:255]
                hx = meta.get("hex")
                if hx and isinstance(hx, str) and len(hx) > 12:
                    hx = hx[:12]
                if not hx:
                    hx = guess_hex_for_slug(cs)
                pc = ProductColor.objects.create(
                    product=product,
                    slug=cs,
                    label=lab,
                    hex=hx,
                    sort_order=order,
                    is_active=True,
                )
                color_by_slug[cs] = pc
                order += 1
                return pc

            for c in color_defs:
                if not isinstance(c, dict):
                    continue
                cs_raw = slugify(str(c.get("slug", "")))
                if not cs_raw:
                    continue
                cs = canonical_color_slug(cs_raw)
                upsert_color(cs, str(c.get("label") or label_from_color_slug(cs)))

            for cs in sorted(color_folder_files.keys()):
                upsert_color(cs, label_from_color_slug(cs))

            if flat_groups:
                for cs in sorted(flat_groups.keys()):
                    upsert_color(cs, label_from_color_slug(cs))

            img_order = 0
            main_color_slugs: set[str] = set()
            global_main_set = False
            added: set[Path] = set()

            def add_image(rel_path: Path, color: ProductColor | None):
                nonlocal img_order, global_main_set
                raw = rel_path.read_bytes()
                webp = bytes_to_webp_on_white(raw)
                name = f"{model_slug_tail}_{img_order:03d}.webp"
                color_slug = color.slug if color else ""
                is_color_main = bool(color_slug and color_slug not in main_color_slugs)
                if is_color_main:
                    main_color_slugs.add(color_slug)
                is_main = is_color_main or (not global_main_set and color is None)
                if is_main and not is_color_main:
                    global_main_set = True
                alt = title
                if color:
                    alt = f"{title} — {color.label}"[:255]
                img = ProductImage(
                    product=product,
                    color=color,
                    is_main=is_main,
                    alt_text=alt[:255],
                    sort_order=img_order,
                )
                img.image.save(name, ContentFile(webp), save=True)
                img_order += 1
                added.add(rel_path.resolve())

            for cs in sorted(color_folder_files.keys()):
                col = color_by_slug.get(cs)
                for f in color_folder_files[cs]:
                    add_image(f, col)

            if flat_groups:
                for cs in sorted(flat_groups.keys()):
                    col = color_by_slug.get(cs)
                    for f in flat_groups[cs]:
                        add_image(f, col)

            if color_defs and not color_folder_files and not flat_groups:
                for c in color_defs:
                    if not isinstance(c, dict):
                        continue
                    cs_raw = slugify(str(c.get("slug", "")))
                    if not cs_raw:
                        continue
                    cs = canonical_color_slug(cs_raw)
                    if cs not in color_by_slug:
                        continue
                    for sd in subdirs:
                        sd_key = canonical_color_slug(slugify(sd.name) or sd.name.lower())
                        if sd_key != cs:
                            continue
                        for f in list_images(sd):
                            add_image(f, color_by_slug[cs])

            for f in root_images:
                if f.resolve() not in added:
                    add_image(f, None)

            stores = list(Store.objects.filter(is_active=True)[:5])
            for store in stores:
                Stock.objects.update_or_create(
                    product=product,
                    store=store,
                    defaults={"quantity": 25, "reserved_quantity": 0},
                )

        self.stdout.write(self.style.SUCCESS(f"  OK: {product_slug}, изображений: {img_order}"))
