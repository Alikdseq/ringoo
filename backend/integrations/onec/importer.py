"""
Планировщик и применение импорта каталога из выгрузки 1С.

По умолчанию — dry-run без записи в БД. Режим apply требует явного флага
и не удаляет категории/товары, которых нет в выгрузке.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any

from django.db import transaction
from django.utils.text import slugify

from apps.products.models import Category, Product
from apps.products.utils import unique_product_slug
from apps.stores.models import Stock, Store

from .parser import (
    MONEY_MAX,
    MONEY_QUANT,
    QTY_MAX,
    OneCFolder,
    OneCParseError,
    OneCProductRow,
    ParsedCatalog,
    parse_catalog_files,
    parse_catalog_xml_strings,
    unique_product_codes,
)


class ImportMode(str, Enum):
    DRY_RUN = "dry_run"
    APPLY = "apply"


APPLE_ROOM_NAMES = frozenset({"apple room", "appleroom"})


@dataclass
class CategoryAction:
    onec_code: str
    name: str
    parent_code: str
    action: str  # create | update | skip
    site_id: str | None = None
    site_slug: str | None = None
    notes: str = ""


@dataclass
class ProductAction:
    onec_code: str
    name: str
    parent_code: str
    price: str | None
    action: str  # create | update | skip | ambiguous
    site_id: str | None = None
    site_slug: str | None = None
    matched_by: str = ""
    notes: str = ""


@dataclass
class StockAction:
    onec_code: str
    sklad: str
    sklad_id: str
    quantity: str | None
    quantity_status: str  # explicit_zero | positive | missing | invalid | rejected
    action: str  # upsert | skip
    notes: str = ""
    series: str = ""
    series_id: str = ""


@dataclass
class CatalogImportPlan:
    mode: str
    generated_at: str
    source_folders_path: str
    source_products_path: str
    folder_count: int = 0
    product_row_count: int = 0
    unique_product_count: int = 0
    categories: list[CategoryAction] = field(default_factory=list)
    products: list[ProductAction] = field(default_factory=list)
    stocks: list[StockAction] = field(default_factory=list)
    warehouses: list[dict[str, Any]] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "generated_at": self.generated_at,
            "source_folders_path": self.source_folders_path,
            "source_products_path": self.source_products_path,
            "folder_count": self.folder_count,
            "product_row_count": self.product_row_count,
            "unique_product_count": self.unique_product_count,
            "summary": self.summary,
            "warehouses": self.warehouses,
            "issues": self.issues,
            "categories": [asdict(c) for c in self.categories],
            "products": [asdict(p) for p in self.products],
            "stocks": [asdict(s) for s in self.stocks],
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _quantity_status(row: OneCProductRow) -> tuple[str | None, str]:
    problem = row.quantity_problem()
    if problem == "empty":
        return None, "missing"
    if problem == "not_a_number":
        return None, "invalid"
    if problem:
        return None, "rejected"
    qty = row.parse_quantity()
    if qty is None:
        return None, "invalid"
    if qty == 0:
        return "0", "explicit_zero"
    return str(qty.to_integral_value()), "positive"


def writable_price(raw: str | None) -> Decimal | None:
    """Повторная проверка непосредственно перед UPDATE/INSERT. Иначе None."""
    if raw is None or str(raw).strip() == "":
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError, ArithmeticError):
        return None
    if not value.is_finite() or value < 0 or value > MONEY_MAX:
        return None
    try:
        if value != value.quantize(MONEY_QUANT):
            return None
    except (InvalidOperation, ValueError, ArithmeticError):
        return None
    return value.quantize(MONEY_QUANT)


def writable_quantity(raw: str | None) -> int | None:
    """Целое >= 0. Отрицательное не превращается в ноль."""
    if raw is None or str(raw).strip() == "":
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError, ArithmeticError):
        return None
    if not value.is_finite() or value < 0 or value > QTY_MAX or value != value.to_integral_value():
        return None
    return int(value)


def _folder_index(folders: list[OneCFolder]) -> dict[str, OneCFolder]:
    return {f.code: f for f in folders}


def _plan_categories(folders: list[OneCFolder]) -> tuple[list[CategoryAction], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    actions: list[CategoryAction] = []
    existing = {
        c.onec_code: c
        for c in Category.objects.exclude(onec_code__isnull=True).exclude(onec_code="")
    }
    by_slug = {c.slug: c for c in Category.objects.all()}

    seen_codes: set[str] = set()
    unique_folders: list[OneCFolder] = []
    for f in folders:
        if f.code in seen_codes:
            issues.append(
                {
                    "type": "folder_duplicate_code",
                    "code": f.code,
                    "name": f.name,
                }
            )
            continue
        seen_codes.add(f.code)
        unique_folders.append(f)
    folders = unique_folders

    # Проверка битых родителей внутри файла
    codes = {f.code for f in folders}
    for f in folders:
        if f.parent_code and f.parent_code not in codes:
            issues.append(
                {
                    "type": "folder_missing_parent",
                    "code": f.code,
                    "parent_code": f.parent_code,
                    "name": f.name,
                }
            )

    # Топологический порядок: сначала без родителя / родители раньше детей
    remaining = list(folders)
    ordered: list[OneCFolder] = []
    seen: set[str] = set()
    while remaining:
        progress = False
        nxt: list[OneCFolder] = []
        for f in remaining:
            if not f.parent_code or f.parent_code in seen or f.parent_code not in codes:
                ordered.append(f)
                seen.add(f.code)
                progress = True
            else:
                nxt.append(f)
        if not progress:
            ordered.extend(nxt)
            break
        remaining = nxt

    for f in ordered:
        if f.code in existing:
            cat = existing[f.code]
            actions.append(
                CategoryAction(
                    onec_code=f.code,
                    name=f.name,
                    parent_code=f.parent_code,
                    action="update",
                    site_id=str(cat.id),
                    site_slug=cat.slug,
                    notes="Сопоставлено по onec_code",
                )
            )
            continue
        slug_guess = slugify(f.name) or slugify(f.code) or f.code.lower()
        hit = by_slug.get(slug_guess)
        if hit and not hit.onec_code:
            actions.append(
                CategoryAction(
                    onec_code=f.code,
                    name=f.name,
                    parent_code=f.parent_code,
                    action="update",
                    site_id=str(hit.id),
                    site_slug=hit.slug,
                    notes="Сопоставлено по slug названия; будет записан onec_code",
                )
            )
        elif hit and hit.onec_code and hit.onec_code != f.code:
            actions.append(
                CategoryAction(
                    onec_code=f.code,
                    name=f.name,
                    parent_code=f.parent_code,
                    action="skip",
                    site_id=str(hit.id),
                    site_slug=hit.slug,
                    notes="Конфликт: slug занят другой категорией с другим onec_code",
                )
            )
            issues.append(
                {
                    "type": "category_slug_conflict",
                    "onec_code": f.code,
                    "slug": hit.slug,
                    "existing_onec_code": hit.onec_code,
                }
            )
        else:
            actions.append(
                CategoryAction(
                    onec_code=f.code,
                    name=f.name,
                    parent_code=f.parent_code,
                    action="create",
                    site_slug=slug_guess,
                    notes="Новая категория; slug сайта сохранится при создании",
                )
            )
    return actions, issues


def _aggregate_products(
    rows: list[OneCProductRow],
) -> dict[str, dict[str, Any]]:
    """Один код 1С → одна карточка; цена — первое непустое; склады отдельно."""
    agg: dict[str, dict[str, Any]] = {}
    for row in rows:
        bucket = agg.setdefault(
            row.code,
            {
                "code": row.code,
                "name": row.name,
                "parent_code": row.parent_code,
                "type_name": row.type_name,
                "prices": [],
                "rows": [],
            },
        )
        if row.name and row.name != bucket["name"]:
            bucket.setdefault("name_variants", set()).add(row.name)
        problem = row.price_problem()
        if problem and problem != "empty":
            bucket.setdefault("price_problems", []).append(
                {"value": (row.price_raw or "")[:64], "reason": problem}
            )
        elif problem is None:
            price = row.parse_price()
            if price is not None:
                bucket["prices"].append(price)
        bucket["rows"].append(row)
        if not bucket["parent_code"] and row.parent_code:
            bucket["parent_code"] = row.parent_code
        if not bucket["type_name"] and row.type_name:
            bucket["type_name"] = row.type_name
    return agg


def _plan_products(
    rows: list[OneCProductRow],
    folder_codes: set[str],
) -> tuple[list[ProductAction], list[StockAction], list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    product_actions: list[ProductAction] = []
    stock_actions: list[StockAction] = []
    warehouses: dict[str, dict[str, Any]] = {}

    existing_by_onec = {
        p.onec_code: p
        for p in Product.objects.exclude(onec_code__isnull=True).exclude(onec_code="")
    }
    existing_by_sku = {
        p.sku: p
        for p in Product.objects.exclude(sku__isnull=True).exclude(sku="")
        if p.sku
    }

    agg = _aggregate_products(rows)

    for code, data in agg.items():
        parent = data["parent_code"]
        if parent and parent not in folder_codes:
            issues.append(
                {
                    "type": "product_missing_category",
                    "onec_code": code,
                    "parent_code": parent,
                    "name": data["name"],
                }
            )

        name_variants = data.get("name_variants") or set()
        if name_variants:
            issues.append(
                {
                    "type": "product_name_variants",
                    "onec_code": code,
                    "names": [data["name"], *sorted(name_variants)],
                }
            )

        prices: list[Decimal] = data["prices"]
        price_problems = list(data.get("price_problems") or [])
        price_str = str(prices[0]) if prices else None
        if price_problems:
            price_str = None
            for problem in price_problems:
                issues.append(
                    {
                        "type": "rejected_price",
                        "onec_code": code,
                        "field": "price",
                        "value": problem.get("value") or "",
                        "reason": problem.get("reason") or "rejected",
                        "name": data["name"],
                        "message": (
                            f"Цена отклонена ({problem.get('reason')}): "
                            f"{problem.get('value')}"
                        ),
                    }
                )
        elif not prices:
            issues.append(
                {
                    "type": "product_missing_price",
                    "onec_code": code,
                    "field": "price",
                    "value": "",
                    "reason": "empty",
                    "name": data["name"],
                    "message": "Пустая цена",
                }
            )
        elif len({str(p) for p in prices}) > 1:
            issues.append(
                {
                    "type": "product_price_variants",
                    "onec_code": code,
                    "prices": [str(p) for p in sorted(set(prices))],
                }
            )
        price_blocked = bool(price_problems) or not prices

        matched = existing_by_onec.get(code)
        matched_by = "onec_code" if matched else ""
        if not matched:
            by_sku = existing_by_sku.get(code)
            if by_sku and not by_sku.onec_code:
                matched = by_sku
                matched_by = "sku_equals_onec_code"
            elif by_sku and by_sku.onec_code and by_sku.onec_code != code:
                product_actions.append(
                    ProductAction(
                        onec_code=code,
                        name=data["name"],
                        parent_code=parent,
                        price=price_str,
                        action="ambiguous",
                        site_id=str(by_sku.id),
                        site_slug=by_sku.slug,
                        matched_by="sku_conflict",
                        notes="SKU совпадает с кодом 1С, но у карточки другой onec_code",
                    )
                )
                issues.append(
                    {
                        "type": "product_sku_conflict",
                        "onec_code": code,
                        "sku": by_sku.sku,
                        "existing_onec_code": by_sku.onec_code,
                    }
                )
                # всё равно планируем остатки для отчёта
            # не матчим только по названию — слишком опасно

        if matched and matched_by:
            product_actions.append(
                ProductAction(
                    onec_code=code,
                    name=data["name"],
                    parent_code=parent,
                    price=price_str,
                    action="update",
                    site_id=str(matched.id),
                    site_slug=matched.slug,
                    matched_by=matched_by,
                    notes="Карточка будет обновлена; slug сайта не меняется",
                )
            )
        elif not any(a.onec_code == code and a.action == "ambiguous" for a in product_actions):
            if parent and parent not in folder_codes:
                product_actions.append(
                    ProductAction(
                        onec_code=code,
                        name=data["name"],
                        parent_code=parent,
                        price=price_str,
                        action="skip",
                        notes="Нет папки в выгрузке — не создаём карточку без согласования",
                    )
                )
            elif price_str is None:
                product_actions.append(
                    ProductAction(
                        onec_code=code,
                        name=data["name"],
                        parent_code=parent,
                        price=None,
                        action="skip",
                        notes="Пустая цена — не публикуем и не создаём без согласования",
                    )
                )
            else:
                product_actions.append(
                    ProductAction(
                        onec_code=code,
                        name=data["name"],
                        parent_code=parent,
                        price=price_str,
                        action="create",
                        notes="Новая карточка; один onec_code — один товар",
                    )
                )

        if price_blocked:
            for action in product_actions:
                if action.onec_code == code and action.action in ("create", "update"):
                    action.action = "skip"
                    action.price = None
                    action.notes = (
                        "Цена отклонена или пустая — карточка не создаётся и не перезаписывается"
                    )

        # Остатки / склады / серии по строкам
        for row in data["rows"]:
            if row.has_warehouse:
                key = row.sklad_id or row.sklad
                warehouses.setdefault(
                    key,
                    {
                        "sklad": row.sklad,
                        "sklad_id": row.sklad_id,
                        "is_apple_room": row.sklad.strip().lower() in APPLE_ROOM_NAMES,
                        "row_count": 0,
                    },
                )
                warehouses[key]["row_count"] += 1

            qty_str, qty_status = _quantity_status(row)
            if not row.has_warehouse:
                stock_actions.append(
                    StockAction(
                        onec_code=code,
                        sklad="",
                        sklad_id="",
                        quantity=None,
                        quantity_status="missing",
                        action="skip",
                        notes="Нет склада и количества — не трактуем как ноль",
                        series=row.series,
                        series_id=row.series_id,
                    )
                )
                continue

            if qty_status == "missing":
                stock_actions.append(
                    StockAction(
                        onec_code=code,
                        sklad=row.sklad,
                        sklad_id=row.sklad_id,
                        quantity=None,
                        quantity_status=qty_status,
                        action="skip",
                        notes="Склад указан, количество пустое — не пишем ноль",
                        series=row.series,
                        series_id=row.series_id,
                    )
                )
                continue

            if qty_status in ("invalid", "rejected"):
                reason = row.quantity_problem() or qty_status
                stock_actions.append(
                    StockAction(
                        onec_code=code,
                        sklad=row.sklad,
                        sklad_id=row.sklad_id,
                        quantity=None,
                        quantity_status=qty_status,
                        action="skip",
                        notes=f"Количество отклонено: {row.quantity_raw!r}",
                        series=row.series,
                        series_id=row.series_id,
                    )
                )
                issues.append(
                    {
                        "type": "rejected_quantity"
                        if qty_status == "rejected"
                        else "invalid_quantity",
                        "onec_code": code,
                        "field": "quantity",
                        "value": (row.quantity_raw or "")[:64],
                        "reason": reason,
                        "sklad": row.sklad,
                        "message": f"Количество отклонено ({reason}): {row.quantity_raw}",
                    }
                )
                continue

            if price_blocked:
                stock_actions.append(
                    StockAction(
                        onec_code=code,
                        sklad=row.sklad,
                        sklad_id=row.sklad_id,
                        quantity=None,
                        quantity_status=qty_status,
                        action="skip",
                        notes="Остаток не пишем: цена этой позиции отклонена",
                        series=row.series,
                        series_id=row.series_id,
                    )
                )
                continue

            note = ""
            if row.has_series:
                note = (
                    f"Серия: {row.series} (seriesID={row.series_id}); "
                    "остаток по серии отдельно от карточки товара"
                )
                issues.append(
                    {
                        "type": "series_present",
                        "onec_code": code,
                        "series": row.series,
                        "series_id": row.series_id,
                        "sklad": row.sklad,
                    }
                )

            stock_actions.append(
                StockAction(
                    onec_code=code,
                    sklad=row.sklad,
                    sklad_id=row.sklad_id,
                    quantity=qty_str,
                    quantity_status=qty_status,
                    action="upsert",
                    notes=note,
                    series=row.series or "",
                    series_id=(row.series_id or "").strip(),
                )
            )

    return product_actions, stock_actions, list(warehouses.values()), issues


def plan_from_parsed(
    parsed: ParsedCatalog,
    *,
    mode: ImportMode = ImportMode.DRY_RUN,
) -> CatalogImportPlan:
    """Планирует импорт из уже разобранного XML (файл или HTTP). Без записи в БД."""
    if parsed.parse_warnings:
        # Пустая/непонятная выгрузка — не планируем apply-опасные действия молча
        raise OneCParseError("; ".join(parsed.parse_warnings))

    folder_codes = {f.code for f in parsed.folders}
    cat_actions, cat_issues = _plan_categories(parsed.folders)
    prod_actions, stock_actions, warehouses, prod_issues = _plan_products(
        parsed.product_rows, folder_codes
    )

    summary = {
        "categories_create": sum(1 for a in cat_actions if a.action == "create"),
        "categories_update": sum(1 for a in cat_actions if a.action == "update"),
        "categories_skip": sum(1 for a in cat_actions if a.action == "skip"),
        "products_create": sum(1 for a in prod_actions if a.action == "create"),
        "products_update": sum(1 for a in prod_actions if a.action == "update"),
        "products_skip": sum(1 for a in prod_actions if a.action == "skip"),
        "products_ambiguous": sum(1 for a in prod_actions if a.action == "ambiguous"),
        "stocks_upsert": sum(1 for a in stock_actions if a.action == "upsert"),
        "stocks_skip": sum(1 for a in stock_actions if a.action == "skip"),
        "warehouses": len(warehouses),
        "issues": len(cat_issues) + len(prod_issues),
        "rejected_positions": sum(
            1
            for i in cat_issues + prod_issues
            if i.get("type") in ("rejected_price", "rejected_quantity", "invalid_quantity")
        ),
        "series_rows": sum(1 for i in prod_issues if i.get("type") == "series_present"),
        "missing_category_products": sum(
            1 for i in prod_issues if i.get("type") == "product_missing_category"
        ),
    }

    return CatalogImportPlan(
        mode=mode.value,
        generated_at=_now_iso(),
        source_folders_path=parsed.source_folders_path,
        source_products_path=parsed.source_products_path,
        folder_count=len(parsed.folders),
        product_row_count=len(parsed.product_rows),
        unique_product_count=len(unique_product_codes(parsed.product_rows)),
        categories=cat_actions,
        products=prod_actions,
        stocks=stock_actions,
        warehouses=warehouses,
        issues=cat_issues + prod_issues,
        summary=summary,
    )


def plan_catalog_import(
    folders_path: str | Path,
    products_path: str | Path,
    *,
    mode: ImportMode = ImportMode.DRY_RUN,
) -> CatalogImportPlan:
    parsed = parse_catalog_files(folders_path, products_path)
    return plan_from_parsed(parsed, mode=mode)


def plan_catalog_import_from_xml_strings(
    folders_xml: str,
    products_xml: str,
    *,
    mode: ImportMode = ImportMode.DRY_RUN,
    source_label: str = "http",
) -> CatalogImportPlan:
    """
    Полный цикл: разбор XML-строк → план.
    При ошибке разбора исключение — БД не трогаем.
    """
    parsed = parse_catalog_xml_strings(
        folders_xml, products_xml, source_label=source_label
    )
    return plan_from_parsed(parsed, mode=mode)


def fetch_and_plan_from_api(
    *,
    mode: ImportMode = ImportMode.DRY_RUN,
    client=None,
) -> CatalogImportPlan:
    """
    GET folders → GET products → разбор → план.
    При HTTP/XML ошибке исключение; предыдущие данные каталога не меняются.
    """
    from .client import OneCClient

    api = client or OneCClient()
    folders_xml = api.fetch_folders_xml()
    products_xml = api.fetch_products_xml()
    return plan_catalog_import_from_xml_strings(
        folders_xml,
        products_xml,
        mode=mode,
        source_label=api.base_url.rstrip("/"),
    )


def write_import_report(plan: CatalogImportPlan, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(plan.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def _unique_category_slug(base: str, *, exclude_id=None) -> str:
    slug = slugify(base) or "category"
    candidate = slug
    n = 2
    qs = Category.objects.all()
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    while qs.filter(slug=candidate).exists():
        candidate = f"{slug}-{n}"
        n += 1
    return candidate


@transaction.atomic
def apply_catalog_import(plan: CatalogImportPlan) -> dict[str, Any]:
    """
    Применяет план к БД. Не удаляет сущности, отсутствующие в выгрузке.
    Остатки пишутся только для строк action=upsert с известным складом и товаром.
    """
    if plan.mode != ImportMode.APPLY.value:
        raise ValueError("apply_catalog_import требует plan.mode=apply")

    folder_by_code = {c.onec_code: c for c in plan.categories if c.action in ("create", "update")}
    # Создаём/обновляем категории в порядке плана (уже топологический из планировщика)
    code_to_category: dict[str, Category] = {}
    for action in plan.categories:
        if action.action == "skip":
            continue
        parent = None
        if action.parent_code:
            parent = code_to_category.get(action.parent_code) or Category.objects.filter(
                onec_code=action.parent_code
            ).first()

        if action.action == "update" and action.site_id:
            cat = Category.objects.get(pk=action.site_id)
            cat.title = action.name
            cat.onec_code = action.onec_code
            if parent:
                cat.parent = parent
            cat.save(update_fields=["title", "onec_code", "parent", "updated_at"])
        else:
            slug = _unique_category_slug(action.site_slug or action.name)
            cat = Category.objects.create(
                title=action.name,
                slug=slug,
                onec_code=action.onec_code,
                parent=parent,
                is_active=True,
            )
        code_to_category[action.onec_code] = cat

    created_products = 0
    updated_products = 0
    for action in plan.products:
        if action.action not in ("create", "update"):
            continue
        category = code_to_category.get(action.parent_code) or Category.objects.filter(
            onec_code=action.parent_code
        ).first()
        if not category:
            continue
        price = writable_price(action.price)
        if price is None:
            continue

        if action.action == "update" and action.site_id:
            product = Product.objects.get(pk=action.site_id)
            product.title = action.name
            product.onec_code = action.onec_code
            product.category = category
            product.price = price
            product.save(
                update_fields=["title", "onec_code", "category", "price", "updated_at"]
            )
            updated_products += 1
        else:
            slug = unique_product_slug(slugify(action.name) or action.onec_code)
            Product.objects.create(
                title=action.name,
                slug=slug,
                sku=action.onec_code,
                onec_code=action.onec_code,
                category=category,
                price=price,
                is_active=True,
            )
            created_products += 1

    # Склады
    store_by_wh: dict[str, Store] = {}
    for wh in plan.warehouses:
        sklad_id = (wh.get("sklad_id") or "").strip()
        sklad = (wh.get("sklad") or "").strip()
        if not sklad_id and not sklad:
            continue
        store = None
        if sklad_id:
            store = Store.objects.filter(onec_warehouse_id=sklad_id).first()
        if not store and sklad:
            store = Store.objects.filter(onec_warehouse_name__iexact=sklad).first()
        if not store and sklad:
            store = Store.objects.filter(name__iexact=sklad).first()
        is_wh = bool(wh.get("is_apple_room"))
        if store:
            dirty = []
            if sklad_id and store.onec_warehouse_id != sklad_id:
                store.onec_warehouse_id = sklad_id
                dirty.append("onec_warehouse_id")
            if sklad and store.onec_warehouse_name != sklad:
                store.onec_warehouse_name = sklad
                dirty.append("onec_warehouse_name")
            if is_wh and not store.is_warehouse:
                store.is_warehouse = True
                dirty.append("is_warehouse")
            if dirty:
                store.save(update_fields=[*dirty, "updated_at"])
        else:
            base_slug = slugify(sklad or sklad_id) or "warehouse"
            slug = base_slug
            n = 2
            while Store.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{n}"
                n += 1
            store = Store.objects.create(
                name=sklad or sklad_id,
                slug=slug,
                address="Уточнить адрес",
                city="Уточнить",
                onec_warehouse_id=sklad_id or None,
                onec_warehouse_name=sklad or None,
                is_warehouse=is_wh,
                is_active=not is_wh,
            )
        key = sklad_id or sklad
        store_by_wh[key] = store

    stock_upserts = 0
    products_by_onec = {
        p.onec_code: p
        for p in Product.objects.exclude(onec_code__isnull=True).exclude(onec_code="")
    }
    for st in plan.stocks:
        if st.action != "upsert":
            continue
        product = products_by_onec.get(st.onec_code)
        if not product:
            continue
        key = st.sklad_id or st.sklad
        store = store_by_wh.get(key)
        if not store:
            continue
        qty = writable_quantity(st.quantity)
        if qty is None:
            continue
        series_id = (getattr(st, "series_id", None) or "").strip()
        series_name = (getattr(st, "series", None) or "").strip()
        from apps.stores.stock_ops import apply_onec_stock_upsert

        apply_onec_stock_upsert(
            product_id=product.pk,
            store_id=store.pk,
            series_id=series_id,
            series_name=series_name,
            quantity=qty,
            idempotency_key=(
                f"onec_import:{product.pk}:{store.pk}:{series_id}:q{qty}"
            ),
        )
        stock_upserts += 1

    return {
        "categories": len(code_to_category),
        "products_created": created_products,
        "products_updated": updated_products,
        "stocks_upserted": stock_upserts,
        "stores_linked": len(store_by_wh),
    }


def diagnose_stale_blank_series_stocks() -> dict[str, Any]:
    """
    Диагностика: строки Stock с пустым onec_series_id при наличии серийных
    остатков того же product+store. Только отчёт — без удаления/обнуления.
    """
    from apps.stores.models import Stock

    serial_pairs = (
        Stock.objects.exclude(onec_series_id="")
        .values_list("product_id", "store_id")
        .distinct()
    )
    serial_set = {(str(p), str(s)) for p, s in serial_pairs}
    suspects = []
    for row in (
        Stock.objects.filter(onec_series_id="")
        .select_related("product", "store")
        .iterator()
    ):
        key = (str(row.product_id), str(row.store_id))
        if key not in serial_set:
            continue
        suspects.append(
            {
                "stock_id": str(row.pk),
                "product_id": str(row.product_id),
                "product_onec_code": getattr(row.product, "onec_code", None),
                "product_title": getattr(row.product, "title", ""),
                "store_id": str(row.store_id),
                "store_slug": getattr(row.store, "slug", ""),
                "quantity": int(row.quantity),
                "reserved_quantity": int(row.reserved_quantity),
                "note": (
                    "Есть серийные остатки того же товара в этом магазине; "
                    "пустая серия может быть устаревшей агрегацией"
                ),
            }
        )
    return {
        "suspect_count": len(suspects),
        "suspects": suspects,
        "action": "report_only",
        "message": (
            "Автоочистка не выполняется. Сверьте с выгрузкой 1С перед правкой данных."
        ),
    }
