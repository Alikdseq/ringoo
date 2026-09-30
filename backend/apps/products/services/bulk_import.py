"""
Массовый импорт товаров из XLSX (+ опционально ZIP с фото по SKU/цвету).
"""

from __future__ import annotations

import io
import zipfile
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify

from apps.products.utils import slugify_product_title, unique_product_slug

from apps.products.models import Category, Product, ProductColor, ProductImage
from apps.products.services.image_pipeline import bytes_to_webp_on_white

ALLOWED_CATEGORY_SLUGS = frozenset({
    "iphone",
    "samsung",
    "huawei",
    "infinix",
    "realme",
    "tecno",
    "xiaomi",
})

REQUIRED_HEADERS = {"sku", "title", "category_slug", "price"}


def _safe_zip_entry_path(name: str) -> bool:
    """Защита от zip-slip и абсолютных путей."""
    normalized = name.replace("\\", "/").strip()
    if not normalized or normalized.startswith("/"):
        return False
    parts = [p for p in normalized.split("/") if p]
    if not parts or any(p == ".." for p in parts):
        return False
    return True

# Русские и английские заголовки → внутреннее имя колонки
COLUMN_ALIASES: dict[str, str] = {
    "sku": "sku",
    "артикул": "sku",
    "title": "title",
    "название": "title",
    "slug": "slug",
    "ссылка": "slug",
    "category_slug": "category_slug",
    "категория": "category_slug",
    "price": "price",
    "цена": "price",
    "old_price": "old_price",
    "старая_цена": "old_price",
    "старая цена": "old_price",
    "brand": "brand",
    "бренд": "brand",
    "description": "description",
    "описание": "description",
    "color_slug": "color_slug",
    "код_цвета": "color_slug",
    "код цвета": "color_slug",
    "color_label": "color_label",
    "название_цвета": "color_label",
    "название цвета": "color_label",
    "color_hex": "color_hex",
    "цвет_hex": "color_hex",
    "цвет hex": "color_hex",
    "color_price": "color_price",
    "цена_цвета": "color_price",
    "цена цвета": "color_price",
    "color_old_price": "color_old_price",
    "старая_цена_цвета": "color_old_price",
    "старая цена цвета": "color_old_price",
}


def _normalize_header(raw: str) -> str:
    key = raw.strip().lower().replace("ё", "е")
    return COLUMN_ALIASES.get(key, key)


def build_import_template_xlsx() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Товары"
    headers = [
        "Артикул (sku)",
        "Название (title)",
        "Ссылка slug",
        "Категория (iphone | samsung)",
        "Цена товара",
        "Старая цена товара",
        "Бренд",
        "Описание",
        "Код цвета",
        "Название цвета",
        "Цвет HEX",
        "Цена цвета",
        "Старая цена цвета",
    ]
    ws.append(headers)
    ws.append(
        [
            "SAM-S24U-256",
            "Samsung Galaxy S24 Ultra 256GB",
            "samsung-galaxy-s24-ultra-256",
            "samsung",
            "119990.00",
            "",
            "Samsung",
            "Флагман Samsung",
            "titanium-gray",
            "Титан серый",
            "#6B6B6B",
            "119990.00",
            "",
        ]
    )
    ws2 = wb.create_sheet("Инструкция")
    instructions = [
        "Как заполнить таблицу",
        "",
        "1. Одна строка = один цвет товара. Одинаковый артикул (sku) объединяется в один товар.",
        "2. Обязательные поля: Артикул, Название, Категория (iphone или samsung), Цена товара.",
        "3. Для каждого цвета укажите: Код цвета (латиницей, например black-titanium), Название цвета, при желании HEX (#1C1C1E).",
        "4. Если у цвета своя цена — заполните «Цена цвета» и при скидке «Старая цена цвета». Иначе берётся цена товара.",
        "5. Фото в ZIP: папка Артикул/Код_цвета/файлы.jpg — фото попадут к этому цвету.",
        "   Общие фото без цвета: Артикул/файлы.jpg",
        "6. Форматы фото: jpg, png, webp. На сайте они конвертируются в webp на белом фоне.",
    ]
    for line in instructions:
        ws2.append([line])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _cell_str(row: dict[str, Any], key: str) -> str:
    v = row.get(key)
    if v is None:
        return ""
    return str(v).strip()


def _parse_decimal(val: str) -> Decimal | None:
    if not val:
        return None
    try:
        return Decimal(str(val).replace(",", ".").replace(" ", ""))
    except (InvalidOperation, ValueError):
        return None


def parse_product_rows(xlsx_bytes: bytes) -> tuple[list[str], list[dict[str, Any]]]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        return ["empty workbook"], []
    headers: list[str] = []
    for c in header_row:
        if c is None:
            headers.append("")
        else:
            headers.append(_normalize_header(str(c)))
    if not headers or not any(headers):
        return ["missing header row"], []

    missing = REQUIRED_HEADERS - set(h for h in headers if h)
    if missing:
        return [f"missing columns: {', '.join(sorted(missing))}"], []

    errors: list[str] = []
    data_rows: list[dict[str, Any]] = []
    for i, row in enumerate(rows_iter, start=2):
        if not row or all(x is None or str(x).strip() == "" for x in row):
            continue
        d = {headers[j]: row[j] if j < len(row) else None for j in range(len(headers))}
        sku = _cell_str(d, "sku")
        if not sku:
            errors.append(f"row {i}: empty sku")
            continue
        data_rows.append(d)
    return errors, data_rows


def _group_by_sku(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Последняя строка с данными товара побеждает; color_* из всех строк с тем же sku."""
    products: dict[str, dict[str, Any]] = {}
    for d in rows:
        sku = _cell_str(d, "sku")
        if sku not in products:
            products[sku] = {"base": {}, "colors": {}}
        base = products[sku]["base"]
        for k in (
            "title",
            "slug",
            "category_slug",
            "price",
            "old_price",
            "brand",
            "description",
        ):
            v = _cell_str(d, k)
            if v:
                base[k] = v
        cs = _cell_str(d, "color_slug")
        if cs:
            prev = products[sku]["colors"].get(cs, {})
            cp = _parse_decimal(_cell_str(d, "color_price"))
            cop = _parse_decimal(_cell_str(d, "color_old_price"))
            products[sku]["colors"][cs] = {
                "label": _cell_str(d, "color_label") or prev.get("label") or cs.replace("-", " ").title(),
                "hex": _cell_str(d, "color_hex") or prev.get("hex"),
                "price": cp if cp is not None else prev.get("price"),
                "old_price": cop if cop is not None else prev.get("old_price"),
            }
    return products


def run_bulk_import(
    xlsx_bytes: bytes,
    zip_bytes: bytes | None,
) -> dict[str, Any]:
    err, rows = parse_product_rows(xlsx_bytes)
    if err and not rows:
        return {"ok": False, "errors": err, "created": 0, "updated": 0, "images": 0}

    grouped = _group_by_sku(rows)
    zip_index: dict[tuple[str, str | None], list[tuple[str, bytes]]] = defaultdict(list)
    if zip_bytes:
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    if not _safe_zip_entry_path(info.filename):
                        continue
                    name = info.filename.replace("\\", "/")
                    parts = [p for p in name.split("/") if p]
                    if not parts or parts[0] == "__MACOSX":
                        continue
                    sku = parts[0]
                    color_slug: str | None = None
                    rel = parts[1:]
                    if len(parts) >= 3:
                        color_slug = parts[1]
                        rel = parts[2:]
                    ext = "." + rel[-1].rsplit(".", 1)[-1].lower() if rel else ""
                    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}:
                        continue
                    raw = zf.read(info.filename)
                    zip_index[(sku, color_slug)].append((rel[-1], raw))
        except zipfile.BadZipFile:
            return {"ok": False, "errors": ["invalid zip archive"], "created": 0, "updated": 0, "images": 0}

    created = 0
    updated = 0
    images_n = 0
    errors = list(err)

    for sku, payload in grouped.items():
        base = payload["base"]
        title = base.get("title", "").strip()
        cat_slug = base.get("category_slug", "").strip().lower()
        if not title:
            errors.append(f"sku {sku}: missing title")
            continue
        if cat_slug not in ALLOWED_CATEGORY_SLUGS:
            errors.append(f"sku {sku}: category_slug must be iphone or samsung")
            continue
        price = _parse_decimal(base.get("price", ""))
        if price is None or price <= 0:
            errors.append(f"sku {sku}: invalid price")
            continue
        old_price = _parse_decimal(base.get("old_price", ""))
        slug_raw = base.get("slug", "").strip()
        title = base.get("title", "").strip() or sku
        if slug_raw:
            slug = unique_product_slug(slugify_product_title(slug_raw))
        else:
            slug = unique_product_slug(slugify_product_title(title) or slugify(sku))
        brand = base.get("brand", "").strip() or None
        desc = base.get("description", "").strip() or ""

        try:
            category = Category.objects.get(slug=cat_slug)
        except Category.DoesNotExist:
            errors.append(f"sku {sku}: category {cat_slug} not found")
            continue

        with transaction.atomic():
            product, was_created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title[:255],
                    "sku": sku[:100],
                    "category": category,
                    "brand": brand,
                    "price": price,
                    "old_price": old_price,
                    "description": desc,
                    "short_description": "",
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

            product.images.all().delete()
            product.colors.all().delete()

            sort_c = 0
            color_by_slug: dict[str, ProductColor] = {}
            for cslug, meta in payload["colors"].items():
                key = slugify(cslug) or (cslug[:100] if cslug else "")
                if not key:
                    continue
                pc = ProductColor.objects.create(
                    product=product,
                    slug=key,
                    label=meta["label"][:255],
                    hex=(meta["hex"][:12] if meta.get("hex") else None),
                    price=meta.get("price"),
                    old_price=meta.get("old_price"),
                    sort_order=sort_c,
                    is_active=True,
                )
                color_by_slug[key] = pc
                sort_c += 1

            for (zsku, zcolor), files in zip_index.items():
                if zsku != sku or not zcolor:
                    continue
                key = slugify(zcolor) or zcolor[:100]
                if key in color_by_slug:
                    continue
                pc = ProductColor.objects.create(
                    product=product,
                    slug=key,
                    label=zcolor.replace("-", " ").replace("_", " ").title()[:255],
                    hex=None,
                    price=None,
                    old_price=None,
                    sort_order=sort_c,
                    is_active=True,
                )
                color_by_slug[key] = pc
                sort_c += 1

            img_order = 0
            first = True

            def save_img(raw: bytes, color: ProductColor | None):
                nonlocal img_order, first, images_n
                webp = bytes_to_webp_on_white(raw)
                name = f"{slug}_{img_order:02d}.webp"
                pi = ProductImage(
                    product=product,
                    color=color,
                    is_main=first,
                    alt_text=title[:255],
                    sort_order=img_order,
                )
                pi.image.save(name, ContentFile(webp), save=True)
                first = False
                img_order += 1
                images_n += 1

            for (zsku, zcolor), files in zip_index.items():
                if zsku != sku:
                    continue
                col_obj = color_by_slug.get(slugify(zcolor)) if zcolor else None
                if zcolor and col_obj is None:
                    col_obj = color_by_slug.get(zcolor)
                for _fname, raw in sorted(files, key=lambda x: x[0]):
                    save_img(raw, col_obj)

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "created": created,
        "updated": updated,
        "images": images_n,
    }
