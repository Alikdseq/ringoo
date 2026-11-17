"""
Планировщик и применение импорта каталога из выгрузки 1С.

По умолчанию — dry-run без записи в БД. Режим apply требует явного флага
и не удаляет категории/товары, которых нет в выгрузке.
"""

from __future__ import annotations

import json
import uuid
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
from .warehouse_map import (
    CONFIRMED_BY_ID,
    CONFIRMED_WAREHOUSE_IDS,
    is_confirmed_warehouse_id,
)


class ImportMode(str, Enum):
    DRY_RUN = "dry_run"
    APPLY = "apply"


class SnapshotPolicy(str, Enum):
    """
    present_only — обновлять только строки из XML; отсутствующие остатки не трогать.
    full_snapshot — полный снимок: отсутствующие на confirmed складах → zero.
    """

    PRESENT_ONLY = "present_only"
    FULL_SNAPSHOT = "full_snapshot"


SNAPSHOT_POLICY_VALUES = frozenset(p.value for p in SnapshotPolicy)


def normalize_snapshot_policy(value: str | SnapshotPolicy | None = None) -> str:
    """Default present_only. Unknown value → ValueError (no silent fallback)."""
    if value is None or value == "":
        return SnapshotPolicy.PRESENT_ONLY.value
    if isinstance(value, SnapshotPolicy):
        return value.value
    text = str(value).strip()
    if text not in SNAPSHOT_POLICY_VALUES:
        raise ValueError(
            f"Unknown snapshot_policy={value!r}; "
            f"allowed: {sorted(SNAPSHOT_POLICY_VALUES)}"
        )
    return text


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
    quantity_status: str  # explicit_zero | positive | missing | invalid | rejected | zeroed
    action: str  # upsert | skip | zero
    notes: str = ""
    series: str = ""
    series_id: str = ""
    site_product_id: str | None = None
    site_store_id: str | None = None


@dataclass
class CatalogImportPlan:
    mode: str
    generated_at: str
    source_folders_path: str
    source_products_path: str
    # Уникальный id запуска плана: стабилен при повторном APPLY того же объекта плана,
    # новый UUID при каждом plan_from_parsed (новый прогон синхронизации).
    run_id: str = ""
    snapshot_policy: str = SnapshotPolicy.PRESENT_ONLY.value
    folder_count: int = 0
    product_row_count: int = 0
    unique_product_count: int = 0
    categories: list[CategoryAction] = field(default_factory=list)
    products: list[ProductAction] = field(default_factory=list)
    stocks: list[StockAction] = field(default_factory=list)
    stocks_to_zero: list[StockAction] = field(default_factory=list)
    warehouses: list[dict[str, Any]] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    apply_blockers: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def apply_allowed(self) -> bool:
        return not self.apply_blockers

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "generated_at": self.generated_at,
            "run_id": self.run_id,
            "snapshot_policy": self.snapshot_policy,
            "source_folders_path": self.source_folders_path,
            "source_products_path": self.source_products_path,
            "folder_count": self.folder_count,
            "product_row_count": self.product_row_count,
            "unique_product_count": self.unique_product_count,
            "summary": self.summary,
            "warehouses": self.warehouses,
            "issues": self.issues,
            "apply_blockers": self.apply_blockers,
            "apply_allowed": self.apply_allowed,
            "categories": [asdict(c) for c in self.categories],
            "products": [asdict(p) for p in self.products],
            "stocks": [asdict(s) for s in self.stocks],
            "stocks_to_zero": [asdict(s) for s in self.stocks_to_zero],
        }

    def ensure_run_id(self) -> str:
        """Гарантирует run_id на плане (для старых объектов / тестов без поля)."""
        if not (self.run_id or "").strip():
            self.run_id = str(uuid.uuid4())
        return self.run_id


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
    existing = {c.onec_code: c for c in Category.objects.exclude(onec_code__isnull=True).exclude(onec_code="")}
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
            bucket.setdefault("price_problems", []).append({"value": (row.price_raw or "")[:64], "reason": problem})
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

    existing_by_onec = {p.onec_code: p for p in Product.objects.exclude(onec_code__isnull=True).exclude(onec_code="")}
    existing_by_sku = {p.sku: p for p in Product.objects.exclude(sku__isnull=True).exclude(sku="") if p.sku}

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
                        "message": (f"Цена отклонена ({problem.get('reason')}): " f"{problem.get('value')}"),
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

        # Карточка: ошибка цены блокирует create/update цены, но не всегда остатки.
        existing_for_stock = None
        if matched and matched_by in ("onec_code", "sku_equals_onec_code"):
            existing_for_stock = matched

        if price_blocked:
            for action in product_actions:
                if action.onec_code == code and action.action in ("create", "update"):
                    action.action = "skip"
                    action.price = None
                    action.notes = "Цена отклонена или пустая — карточка не создаётся и не перезаписывается"

        # Остатки / склады / серии по строкам
        for row in data["rows"]:
            sklad_id = (row.sklad_id or "").strip()
            if row.has_warehouse:
                key = sklad_id or row.sklad
                meta = CONFIRMED_BY_ID.get(sklad_id)
                warehouses.setdefault(
                    key,
                    {
                        "sklad": row.sklad,
                        "sklad_id": sklad_id,
                        "is_warehouse": bool(meta.is_warehouse) if meta else False,
                        "is_confirmed": is_confirmed_warehouse_id(sklad_id),
                        "row_count": 0,
                    },
                )
                warehouses[key]["row_count"] += 1

            qty_str, qty_status = _quantity_status(row)
            series_id = (row.series_id or "").strip()
            series_name = (row.series or "").strip()

            if not row.has_warehouse:
                stock_actions.append(
                    StockAction(
                        onec_code=code,
                        sklad="",
                        sklad_id="",
                        quantity=None,
                        quantity_status="missing",
                        action="skip",
                        notes="Нет склада — строка не участвует в снимке",
                        series=series_name,
                        series_id=series_id,
                    )
                )
                issues.append(
                    {
                        "type": "stock_row_no_warehouse",
                        "severity": True,
                        "onec_code": code,
                        "message": "Строка без склада — нельзя безопасно сверить снимок",
                    }
                )
                continue

            if not sklad_id:
                stock_actions.append(
                    StockAction(
                        onec_code=code,
                        sklad=row.sklad,
                        sklad_id="",
                        quantity=None,
                        quantity_status=qty_status,
                        action="skip",
                        notes="Склад без warehouseId — сопоставление запрещено",
                        series=series_name,
                        series_id=series_id,
                    )
                )
                issues.append(
                    {
                        "type": "warehouse_missing_id",
                        "severity": True,
                        "onec_code": code,
                        "sklad": row.sklad,
                        "message": f"Склад без warehouseId: {row.sklad!r}",
                    }
                )
                continue

            if not is_confirmed_warehouse_id(sklad_id):
                stock_actions.append(
                    StockAction(
                        onec_code=code,
                        sklad=row.sklad,
                        sklad_id=sklad_id,
                        quantity=None,
                        quantity_status=qty_status,
                        action="skip",
                        notes="Неизвестный warehouseId — Store не создаём",
                        series=series_name,
                        series_id=series_id,
                    )
                )
                issues.append(
                    {
                        "type": "unknown_warehouse",
                        "severity": True,
                        "onec_code": code,
                        "sklad": row.sklad,
                        "sklad_id": sklad_id,
                        "message": f"Неизвестный warehouseId: {sklad_id}",
                    }
                )
                continue

            if series_name and not series_id:
                stock_actions.append(
                    StockAction(
                        onec_code=code,
                        sklad=row.sklad,
                        sklad_id=sklad_id,
                        quantity=None,
                        quantity_status=qty_status,
                        action="skip",
                        notes="Серия без seriesId — неоднозначно",
                        series=series_name,
                        series_id="",
                    )
                )
                issues.append(
                    {
                        "type": "series_missing_id",
                        "severity": True,
                        "onec_code": code,
                        "sklad_id": sklad_id,
                        "series": series_name,
                        "message": "series без seriesId",
                    }
                )
                continue

            if qty_status == "missing":
                stock_actions.append(
                    StockAction(
                        onec_code=code,
                        sklad=row.sklad,
                        sklad_id=sklad_id,
                        quantity=None,
                        quantity_status=qty_status,
                        action="skip",
                        notes="Склад указан, количество пустое — не пишем ноль из строки",
                        series=series_name,
                        series_id=series_id,
                    )
                )
                issues.append(
                    {
                        "type": "quantity_empty_with_warehouse",
                        "severity": True,
                        "onec_code": code,
                        "sklad_id": sklad_id,
                        "message": "Пустое quantity при указанном складе",
                    }
                )
                continue

            if qty_status in ("invalid", "rejected"):
                reason = row.quantity_problem() or qty_status
                stock_actions.append(
                    StockAction(
                        onec_code=code,
                        sklad=row.sklad,
                        sklad_id=sklad_id,
                        quantity=None,
                        quantity_status=qty_status,
                        action="skip",
                        notes=f"Количество отклонено: {row.quantity_raw!r}",
                        series=series_name,
                        series_id=series_id,
                    )
                )
                issues.append(
                    {
                        "type": "rejected_quantity" if qty_status == "rejected" else "invalid_quantity",
                        "severity": True,
                        "onec_code": code,
                        "field": "quantity",
                        "value": (row.quantity_raw or "")[:64],
                        "reason": reason,
                        "sklad": row.sklad,
                        "sklad_id": sklad_id,
                        "message": f"Количество отклонено ({reason}): {row.quantity_raw}",
                    }
                )
                continue

            # Новый товар без цены: нельзя создать Product → нельзя писать Stock.
            # Существующая карточка: остатки обновляем даже при price_blocked.
            if price_blocked and existing_for_stock is None:
                stock_actions.append(
                    StockAction(
                        onec_code=code,
                        sklad=row.sklad,
                        sklad_id=sklad_id,
                        quantity=None,
                        quantity_status=qty_status,
                        action="skip",
                        notes="Нет карточки и цена отклонена — Stock не создаём",
                        series=series_name,
                        series_id=series_id,
                    )
                )
                continue

            # Нет сопоставленной/создаваемой карточки (ambiguous / missing category)
            can_create = any(a.onec_code == code and a.action == "create" for a in product_actions)
            if existing_for_stock is None and not can_create:
                stock_actions.append(
                    StockAction(
                        onec_code=code,
                        sklad=row.sklad,
                        sklad_id=sklad_id,
                        quantity=qty_str,
                        quantity_status=qty_status,
                        action="skip",
                        notes="Нет Product для остатка — строка в снимке не учитывается",
                        series=series_name,
                        series_id=series_id,
                    )
                )
                issues.append(
                    {
                        "type": "stock_without_product",
                        "severity": True,
                        "onec_code": code,
                        "sklad_id": sklad_id,
                        "message": "Остаток без сопоставленной карточки",
                    }
                )
                continue

            note = ""
            if series_id:
                note = f"Серия: {series_name} (seriesID={series_id}); " "остаток по серии отдельно от карточки товара"
                issues.append(
                    {
                        "type": "series_present",
                        "onec_code": code,
                        "series": series_name,
                        "series_id": series_id,
                        "sklad": row.sklad,
                    }
                )

            stock_actions.append(
                StockAction(
                    onec_code=code,
                    sklad=row.sklad,
                    sklad_id=sklad_id,
                    quantity=qty_str,
                    quantity_status=qty_status,
                    action="upsert",
                    notes=note,
                    series=series_name,
                    series_id=series_id,
                    site_product_id=str(existing_for_stock.pk) if existing_for_stock is not None else None,
                )
            )

    return product_actions, stock_actions, list(warehouses.values()), issues


def _stores_by_confirmed_warehouse_id() -> dict[str, Store]:
    return {
        (s.onec_warehouse_id or "").strip(): s
        for s in Store.objects.filter(onec_warehouse_id__in=CONFIRMED_WAREHOUSE_IDS)
        if (s.onec_warehouse_id or "").strip()
    }


def _narrow_stock_skip_missing_category(
    *,
    issues: list[dict[str, Any]],
    stock_actions: list[StockAction],
    product_actions: list[ProductAction],
) -> int:
    """
    Узкое исключение этапа C (один CatalogImportPlan, строго по onec_code):

    Если для кода одновременно есть product_missing_category и stock_without_product,
    и карточка в плане — ProductAction(action=skip) с parent_code (не ambiguous),
    то складские строки этого кода не блокируют APPLY:
      stock_without_product → stock_skipped_missing_category (severity=False).

    Eligibility не зависит от текста notes.
    Любая другая причина stock_without_product остаётся blocker.
    Category автоматически не создаём.
    """
    missing_cat_codes = {
        (i.get("onec_code") or "").strip()
        for i in issues
        if (i.get("type") or "") == "product_missing_category" and (i.get("onec_code") or "").strip()
    }
    if not missing_cat_codes:
        return 0

    ambiguous_codes = {a.onec_code for a in product_actions if a.action == "ambiguous"}
    # Структурно (без текста notes): skip + parent_code + issue product_missing_category,
    # не ambiguous. Другие skip (цена и т.п.) не попадают в missing_cat_codes.
    skip_missing_codes = {
        a.onec_code
        for a in product_actions
        if a.action == "skip"
        and a.onec_code in missing_cat_codes
        and a.onec_code not in ambiguous_codes
        and (a.parent_code or "").strip()
    }
    eligible = missing_cat_codes & skip_missing_codes
    if not eligible:
        return 0

    converted = 0
    for issue in issues:
        if (issue.get("type") or "") != "stock_without_product":
            continue
        code = (issue.get("onec_code") or "").strip()
        if code not in eligible:
            continue
        issue["type"] = "stock_skipped_missing_category"
        issue["severity"] = False
        issue.pop("blocker", None)
        issue["reason"] = "product_missing_category"
        issue["message"] = (
            "Остаток пропущен: карточка не создана из‑за отсутствующей "
            f"родительской категории (onec_code={code})"
        )
        converted += 1

    if converted:
        for st in stock_actions:
            if st.action != "skip" or st.onec_code not in eligible:
                continue
            if "Нет Product для остатка" not in (st.notes or ""):
                continue
            st.notes = (
                "Пропуск остатка: product_missing_category — карточка не создана, "
                "Category автоматически не создаём"
            )

    return converted


def _collect_apply_blockers(
    *,
    issues: list[dict[str, Any]],
    warehouses: list[dict[str, Any]],
    store_by_wid: dict[str, Store],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for issue in issues:
        # Issues may mark fail-closed rows as blocker=True or severity=True.
        if issue.get("blocker") or issue.get("severity"):
            blockers.append(
                {
                    "type": issue.get("type") or "blocker",
                    "message": issue.get("message") or str(issue),
                    "sklad_id": issue.get("sklad_id") or "",
                    "onec_code": issue.get("onec_code") or "",
                }
            )

    for wid in sorted(CONFIRMED_WAREHOUSE_IDS):
        if wid not in store_by_wid:
            meta = CONFIRMED_BY_ID[wid]
            blockers.append(
                {
                    "type": "confirmed_warehouse_unmapped",
                    "message": (
                        f"Склад 1С «{meta.onec_name}» ({wid}) не привязан к Store. "
                        f"Выполните list_onec_warehouses --apply "
                        f"(suggested slug={meta.suggested_slug})."
                    ),
                    "sklad_id": wid,
                }
            )

    for wh in warehouses:
        wid = (wh.get("sklad_id") or "").strip()
        if wid and wid not in CONFIRMED_WAREHOUSE_IDS:
            blockers.append(
                {
                    "type": "unknown_warehouse",
                    "message": f"Неизвестный warehouseId в выгрузке: {wid}",
                    "sklad_id": wid,
                }
            )

    # Уникализируем по (type, sklad_id, onec_code, message)
    uniq: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    for b in blockers:
        key = (b.get("type"), b.get("sklad_id"), b.get("onec_code"), b.get("message"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(b)
    return uniq


def _plan_stocks_to_zero(
    *,
    seen_keys: set[tuple[str, str, str]],
    store_by_wid: dict[str, Store],
) -> list[StockAction]:
    """
    Позиции Stock на подтверждённых складах, которых нет в полном снимке.
    Карточки Product не трогаем.
    """
    if not store_by_wid:
        return []
    store_ids = [s.pk for s in store_by_wid.values()]
    zeros: list[StockAction] = []
    qs = (
        Stock.objects.filter(store_id__in=store_ids)
        .exclude(product__onec_code__isnull=True)
        .exclude(product__onec_code="")
        .filter(quantity__gt=0)
        .select_related("product", "store")
    )
    for row in qs.iterator():
        key = (
            str(row.product_id),
            str(row.store_id),
            (row.onec_series_id or "").strip(),
        )
        if key in seen_keys:
            continue
        zeros.append(
            StockAction(
                onec_code=row.product.onec_code or "",
                sklad=row.store.onec_warehouse_name or row.store.name,
                sklad_id=row.store.onec_warehouse_id or "",
                quantity="0",
                quantity_status="zeroed",
                action="zero",
                notes="Отсутствует в полном снимке 1С — обнуляем физический остаток",
                series=row.onec_series_name or "",
                series_id=(row.onec_series_id or "").strip(),
                site_product_id=str(row.product_id),
                site_store_id=str(row.store_id),
            )
        )
    return zeros


def plan_from_parsed(
    parsed: ParsedCatalog,
    *,
    mode: ImportMode = ImportMode.DRY_RUN,
    snapshot_policy: str | SnapshotPolicy | None = None,
) -> CatalogImportPlan:
    """Планирует импорт из уже разобранного XML (файл или HTTP). Без записи в БД."""
    policy = normalize_snapshot_policy(snapshot_policy)
    if parsed.parse_warnings:
        # Пустая/непонятная выгрузка — не планируем apply-опасные действия молча
        raise OneCParseError("; ".join(parsed.parse_warnings))

    folder_codes = {f.code for f in parsed.folders}
    cat_actions, cat_issues = _plan_categories(parsed.folders)
    prod_actions, stock_actions, warehouses, prod_issues = _plan_products(parsed.product_rows, folder_codes)
    all_issues = cat_issues + prod_issues

    # Этап C: узкий skip остатков только при доказанном product_missing_category того же onec_code.
    skipped_stocks_missing_category = _narrow_stock_skip_missing_category(
        issues=all_issues,
        stock_actions=stock_actions,
        product_actions=prod_actions,
    )

    store_by_wid = _stores_by_confirmed_warehouse_id()
    apply_blockers = _collect_apply_blockers(issues=all_issues, warehouses=warehouses, store_by_wid=store_by_wid)

    # Привязка upsert → site ids для seen_keys
    products_by_onec = {p.onec_code: p for p in Product.objects.exclude(onec_code__isnull=True).exclude(onec_code="")}
    seen_keys: set[tuple[str, str, str]] = set()
    for st in stock_actions:
        if st.action != "upsert":
            continue
        product = None
        if st.site_product_id:
            product = products_by_onec.get(st.onec_code)
        else:
            product = products_by_onec.get(st.onec_code)
        # Новые create ещё без PK — seen после apply; для плана zero учитываем
        # только уже существующие product+store. Create+upsert в том же apply
        # не порождает «stale» до первого появления.
        if product is None:
            continue
        store = store_by_wid.get((st.sklad_id or "").strip())
        if store is None:
            continue
        st.site_product_id = str(product.pk)
        st.site_store_id = str(store.pk)
        seen_keys.add((str(product.pk), str(store.pk), (st.series_id or "").strip()))

    # present_only: отсутствие в XML ≠ ноль. Zero-фаза только для full_snapshot.
    stocks_to_zero: list[StockAction] = []
    if policy == SnapshotPolicy.FULL_SNAPSHOT.value and not apply_blockers:
        stocks_to_zero = _plan_stocks_to_zero(seen_keys=seen_keys, store_by_wid=store_by_wid)

    from integrations.onec.reporting import build_issue_counts, partition_issues

    partitioned = partition_issues(all_issues)
    issue_counts = build_issue_counts(partitioned)
    series_stock_rows = sum(1 for a in stock_actions if a.action == "upsert" and (a.series_id or "").strip())
    summary = {
        # Planned (ожидаемые действия плана; для APPLY фактические — из apply_result)
        "snapshot_policy": policy,
        "categories_create": sum(1 for a in cat_actions if a.action == "create"),
        "categories_update": sum(1 for a in cat_actions if a.action == "update"),
        "categories_skip": sum(1 for a in cat_actions if a.action == "skip"),
        "products_create": sum(1 for a in prod_actions if a.action == "create"),
        "products_update": sum(1 for a in prod_actions if a.action == "update"),
        "products_skip": sum(1 for a in prod_actions if a.action == "skip"),
        "products_ambiguous": sum(1 for a in prod_actions if a.action == "ambiguous"),
        "stocks_upsert": sum(1 for a in stock_actions if a.action == "upsert"),
        "stocks_skip": sum(1 for a in stock_actions if a.action == "skip"),
        "stocks_to_zero": len(stocks_to_zero),
        "stock_series_rows": series_stock_rows,
        "seen_keys": len(seen_keys),
        "warehouses": len(warehouses),
        "xml_product_rows": len(parsed.product_rows),
        "xml_folder_rows": len(parsed.folders),
        "unique_products": len(unique_product_codes(parsed.product_rows)),
        "apply_allowed": not apply_blockers,
        "apply_blockers": len(apply_blockers),
        "issues": len(all_issues),
        "rejected_positions": sum(
            1 for i in all_issues if i.get("type") in ("rejected_price", "rejected_quantity", "invalid_quantity")
        ),
        "series_rows": issue_counts["series_rows"],
        "missing_category_products": sum(1 for i in all_issues if i.get("type") == "product_missing_category"),
        "skipped_stocks_missing_category": skipped_stocks_missing_category,
        **issue_counts,
    }

    return CatalogImportPlan(
        mode=mode.value,
        generated_at=_now_iso(),
        run_id=str(uuid.uuid4()),
        snapshot_policy=policy,
        source_folders_path=parsed.source_folders_path,
        source_products_path=parsed.source_products_path,
        folder_count=len(parsed.folders),
        product_row_count=len(parsed.product_rows),
        unique_product_count=len(unique_product_codes(parsed.product_rows)),
        categories=cat_actions,
        products=prod_actions,
        stocks=stock_actions,
        stocks_to_zero=stocks_to_zero,
        warehouses=warehouses,
        issues=all_issues,
        apply_blockers=apply_blockers,
        summary=summary,
    )


def plan_catalog_import(
    folders_path: str | Path,
    products_path: str | Path,
    *,
    mode: ImportMode = ImportMode.DRY_RUN,
    snapshot_policy: str | SnapshotPolicy | None = None,
) -> CatalogImportPlan:
    parsed = parse_catalog_files(folders_path, products_path)
    return plan_from_parsed(parsed, mode=mode, snapshot_policy=snapshot_policy)


def plan_catalog_import_from_xml_strings(
    folders_xml: str,
    products_xml: str,
    *,
    mode: ImportMode = ImportMode.DRY_RUN,
    source_label: str = "http",
    snapshot_policy: str | SnapshotPolicy | None = None,
) -> CatalogImportPlan:
    """
    Полный цикл: разбор XML-строк → план.
    При ошибке разбора исключение — БД не трогаем.
    """
    parsed = parse_catalog_xml_strings(folders_xml, products_xml, source_label=source_label)
    return plan_from_parsed(parsed, mode=mode, snapshot_policy=snapshot_policy)


def fetch_and_plan_from_api(
    *,
    mode: ImportMode = ImportMode.DRY_RUN,
    client=None,
    snapshot_policy: str | SnapshotPolicy | None = None,
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
        snapshot_policy=snapshot_policy,
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


def apply_catalog_import(*args, **kwargs):
    """
    Устаревший вход закрыт (D.2.1/D.2.3).
    Используйте integrations.onec.plan_store.apply_saved_plan(plan_id, ...).
    """
    raise PermissionError(
        "apply_catalog_import(plan) закрыт. "
        "APPLY только через plan_store.apply_saved_plan(plan_id) "
        "после DRY-RUN с сохранённым plan_id."
    )


def apply_catalog_import_by_plan_id(
    plan_id,
    *,
    full_snapshot_acknowledged: bool = False,
) -> dict[str, Any]:
    """Публичный APPLY — делегирует в plan_store.apply_saved_plan."""
    from integrations.onec.plan_store import apply_saved_plan

    return apply_saved_plan(
        plan_id, full_snapshot_acknowledged=full_snapshot_acknowledged
    )


@transaction.atomic
def _apply_catalog_import_plan(
    plan: CatalogImportPlan,
    *,
    gate,
    expected_plan_id,
) -> dict[str, Any]:
    """
    Внутреннее применение плана после consume execution_token.
    Вызывается только из plan_store.apply_saved_plan.

    Не удаляет/не деактивирует карточки Product.
    Store не создаёт — только склады с подтверждённым onec_warehouse_id.
    Zero-phase выполняется только при snapshot_policy=full_snapshot.

    ONEC-014: одна atomic на весь apply.
    """
    from integrations.onec.plan_store import validate_and_consume_execution_gate

    validate_and_consume_execution_gate(gate, expected_plan_id=expected_plan_id)
    if plan.mode != ImportMode.APPLY.value:
        raise ValueError("apply требует plan.mode=apply")
    if plan.apply_blockers:
        raise ValueError(
            "apply заблокирован: "
            + "; ".join((b.get("message") or b.get("type") or "blocker") for b in plan.apply_blockers[:5])
        )
    policy = normalize_snapshot_policy(getattr(plan, "snapshot_policy", None))
    if plan.stocks_to_zero and policy != SnapshotPolicy.FULL_SNAPSHOT.value:
        raise ValueError(
            "stocks_to_zero допустимы только при snapshot_policy=full_snapshot "
            f"(получено {policy!r})"
        )
    # Создаём/обновляем категории в порядке плана (уже топологический из планировщика)
    code_to_category: dict[str, Category] = {}
    for action in plan.categories:
        if action.action == "skip":
            continue
        parent = None
        if action.parent_code:
            parent = (
                code_to_category.get(action.parent_code)
                or Category.objects.filter(onec_code=action.parent_code).first()
            )

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
        category = (
            code_to_category.get(action.parent_code) or Category.objects.filter(onec_code=action.parent_code).first()
        )
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
            product.save(update_fields=["title", "onec_code", "category", "price", "updated_at"])
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

    # Склады: только по подтверждённому warehouseId, без create и без match по имени.
    store_by_wid = _stores_by_confirmed_warehouse_id()
    for wh in plan.warehouses:
        sklad_id = (wh.get("sklad_id") or "").strip()
        if not sklad_id or sklad_id not in store_by_wid:
            continue
        store = store_by_wid[sklad_id]
        sklad = (wh.get("sklad") or "").strip()
        meta = CONFIRMED_BY_ID.get(sklad_id)
        dirty: list[str] = []
        if sklad and store.onec_warehouse_name != sklad:
            store.onec_warehouse_name = sklad
            dirty.append("onec_warehouse_name")
        if meta and store.is_warehouse != meta.is_warehouse:
            store.is_warehouse = meta.is_warehouse
            dirty.append("is_warehouse")
        if dirty:
            store.save(update_fields=[*dirty, "updated_at"])

    stock_upserts = 0
    stock_zeros = 0
    stock_skipped_idempotent = 0
    run_id = plan.ensure_run_id()
    products_by_onec = {p.onec_code: p for p in Product.objects.exclude(onec_code__isnull=True).exclude(onec_code="")}
    from apps.stores.stock_ops import (
        OnecStockUpsertItem,
        apply_onec_stock_upserts_batch,
    )

    # BLOCK 6: batch upsert/zero внутри той же atomic (ONEC-014), без построчного
    # N+1 (StockMovement lookup + update_or_create + movement insert).
    upsert_items: list[OnecStockUpsertItem] = []
    for st in plan.stocks:
        if st.action != "upsert":
            continue
        product = products_by_onec.get(st.onec_code)
        if not product:
            continue
        store = store_by_wid.get((st.sklad_id or "").strip())
        if not store:
            continue
        qty = writable_quantity(st.quantity)
        if qty is None:
            continue
        upsert_items.append(
            OnecStockUpsertItem(
                product_id=product.pk,
                store_id=store.pk,
                series_id=(getattr(st, "series_id", None) or "").strip(),
                series_name=(getattr(st, "series", None) or "").strip(),
                quantity=qty,
            )
        )

    zero_items: list[OnecStockUpsertItem] = []
    # Defense: zero-фаза только full_snapshot (present_only план обязан иметь пустой stocks_to_zero).
    if policy == SnapshotPolicy.FULL_SNAPSHOT.value:
        for st in plan.stocks_to_zero:
            if st.action != "zero":
                continue
            product_id = st.site_product_id
            store_id = st.site_store_id
            if not product_id or not store_id:
                continue
            zero_items.append(
                OnecStockUpsertItem(
                    product_id=product_id,
                    store_id=store_id,
                    series_id=(st.series_id or "").strip(),
                    series_name=(st.series or "").strip(),
                    quantity=0,
                )
            )

    if upsert_items:
        up = apply_onec_stock_upserts_batch(upsert_items, run_id=run_id)
        stock_upserts = up["applied"]
        stock_skipped_idempotent += up["skipped_idempotent"]
    if zero_items:
        zr = apply_onec_stock_upserts_batch(zero_items, run_id=run_id)
        stock_zeros = zr["applied"]
        stock_skipped_idempotent += zr["skipped_idempotent"]

    reserved_over = diagnose_reserved_over_quantity()
    return {
        "categories": len(code_to_category),
        "products_created": created_products,
        "products_updated": updated_products,
        "stocks_upserted": stock_upserts,
        "stocks_zeroed": stock_zeros,
        "stocks_skipped_idempotent": stock_skipped_idempotent,
        "stores_linked": len(store_by_wid),
        "run_id": run_id,
        "reserved_over_quantity_count": reserved_over["anomaly_count"],
    }


def diagnose_stale_blank_series_stocks() -> dict[str, Any]:
    """
    Диагностика: строки Stock с пустым onec_series_id при наличии серийных
    остатков того же product+store. Только отчёт — без удаления/обнуления.
    """
    from apps.stores.models import Stock

    serial_pairs = Stock.objects.exclude(onec_series_id="").values_list("product_id", "store_id").distinct()
    serial_set = {(str(p), str(s)) for p, s in serial_pairs}
    suspects = []
    for row in Stock.objects.filter(onec_series_id="").select_related("product", "store").iterator():
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
        "message": ("Автоочистка не выполняется. Сверьте с выгрузкой 1С перед правкой данных."),
    }


def diagnose_reserved_over_quantity() -> dict[str, Any]:
    """
    ONEC-004: Stock, где reserved_quantity > quantity.
    Только отчёт — резерв не режем и не затираем автоматически.
    """
    from django.db.models import F

    from apps.stores.models import Stock

    rows = []
    qs = (
        Stock.objects.filter(reserved_quantity__gt=F("quantity"))
        .select_related("product", "store")
        .order_by("store__slug", "product__onec_code")
    )
    for row in qs.iterator():
        qty = int(row.quantity)
        reserved = int(row.reserved_quantity)
        rows.append(
            {
                "stock_id": str(row.pk),
                "product_id": str(row.product_id),
                "product_onec_code": getattr(row.product, "onec_code", None),
                "product_title": getattr(row.product, "title", ""),
                "store_id": str(row.store_id),
                "store_slug": getattr(row.store, "slug", ""),
                "onec_series_id": (row.onec_series_id or "").strip(),
                "quantity": qty,
                "reserved_quantity": reserved,
                "available_quantity": max(0, qty - reserved),
                "deficit": reserved - qty,
                "note": ("reserved > quantity; available=0 до пополнения. " "Резерв не уменьшается автоматически."),
            }
        )
    return {
        "anomaly_count": len(rows),
        "anomalies": rows,
        "action": "report_only",
        "message": ("Автоисправление резерва не выполняется. " "Проверьте незакрытые заказы / sync после продажи."),
    }
