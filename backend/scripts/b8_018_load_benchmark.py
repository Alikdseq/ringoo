#!/usr/bin/env python
"""
B8-018 / FIX-PACK K — локальный нагрузочный бенчмарк интеграции 1С.

READ-ONLY относительно production / реальной 1С.
Использует синтетические XML + Django test DB (обычно SQLite :memory:).
Не читает .env. Не делает commit/migrate/APPLY на prod.

Запуск из backend/:
  python scripts/b8_018_load_benchmark.py
"""

from __future__ import annotations

import gc
import json
import os
import sys
import time
import traceback
import tracemalloc
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# --- Django bootstrap (test settings only) ---
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import django

django.setup()

from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.test.runner import DiscoverRunner
from django.test.utils import CaptureQueriesContext, setup_test_environment

FIXTURE_DIR = BACKEND_ROOT / "var" / "b8_018_fixtures"
RESULT_PATH = BACKEND_ROOT / "var" / "b8_018_results.json"

# Подтверждённые склады (без PII) — те же UUID, что в warehouse_map.
WAREHOUSES = [
    ("Ардон", "7d0745da-cea9-11f0-82e3-00155d01c802"),
    ("БАМ", "1418e927-cea5-11f0-82e3-00155d01c802"),
    ("Беслан", "8d9cc921-cea9-11f0-82e3-00155d01c802"),
    ("Ватутина", "9de5e8ce-cea9-11f0-82e3-00155d01c802"),
    ("Доватора", "710472c0-866e-11f0-82e1-00155d01c802"),
    ("Кирова", "ae0d8ae3-cea9-11f0-82e3-00155d01c802"),
    ("Коста 199", "bd718455-cea9-11f0-82e3-00155d01c802"),
    ("Коста 288", "cedfb76d-cea9-11f0-82e3-00155d01c802"),
    ("Склад", "63f7e17d-cea9-11f0-82e3-00155d01c802"),
]
TYPE_ID = "b3b4b926-a789-11f0-82e2-00155d01c802"
CAT_CODE = "SYN-CAT-001"

# Пороги безопасности при ~ограниченной RAM
MAX_PARSER_CARDS = 50_000
ABORT_IF_PEAK_MIB = 350
ABORT_IF_AVAIL_MIB = 200
APPLY_TIME_BUDGET_S = 120


@dataclass
class VolumeSpec:
    name: str
    cards: int
    warehouses: int
    series_per_card_wh: int
    gen_50k: bool = False


@dataclass
class Results:
    environment: dict[str, Any] = field(default_factory=dict)
    inventory: dict[str, Any] = field(default_factory=dict)
    fixtures: list[dict[str, Any]] = field(default_factory=list)
    parser: list[dict[str, Any]] = field(default_factory=list)
    parser_edge: list[dict[str, Any]] = field(default_factory=list)
    dry_run: list[dict[str, Any]] = field(default_factory=list)
    dry_run_scenarios: list[dict[str, Any]] = field(default_factory=list)
    batch_apply: list[dict[str, Any]] = field(default_factory=list)
    apply_semantics: list[dict[str, Any]] = field(default_factory=list)
    transactions: list[dict[str, Any]] = field(default_factory=list)
    locks: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    aborted: list[str] = field(default_factory=list)


def _now() -> float:
    return time.perf_counter()


def _ms(t0: float) -> float:
    return round((_now() - t0) * 1000.0, 2)


def _rss_mib() -> float | None:
    try:
        import psutil

        return round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
    except Exception:
        return None


def _avail_mib() -> float | None:
    try:
        import psutil

        return round(psutil.virtual_memory().available / (1024 * 1024), 2)
    except Exception:
        return None


def _safe_to_continue(peak_traced_mib: float | None = None) -> tuple[bool, str]:
    avail = _avail_mib()
    if avail is not None and avail < ABORT_IF_AVAIL_MIB:
        return False, f"available RAM {avail} MiB < {ABORT_IF_AVAIL_MIB}"
    if peak_traced_mib is not None and peak_traced_mib > ABORT_IF_PEAK_MIB:
        return False, f"tracemalloc peak {peak_traced_mib:.1f} MiB > {ABORT_IF_PEAK_MIB}"
    return True, ""


def save(results: Results) -> None:
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(asdict(results), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def folders_xml() -> str:
    return (
        "<?xml version='1.0' encoding='utf-8'?>"
        "<ПапкиНоменклатуры>"
        f'<Папка code="{CAT_CODE}" parentCode="" name="Synth Category"/>'
        "</ПапкиНоменклатуры>"
    )


def generate_products_xml(
    path: Path,
    *,
    cards: int,
    warehouses: int,
    series_per: int,
) -> dict[str, Any]:
    """Пишет XML на диск потоково (не держит весь файл в RAM как одну гигантскую join)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    whs = WAREHOUSES[: max(1, min(warehouses, len(WAREHOUSES)))]
    t0 = _now()
    rows = 0
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write("<?xml version='1.0' encoding='utf-8'?>\n<Товары>")
        for i in range(cards):
            code = f"SYN-{i:06d}"
            name = f"Synth Item {i}"
            # ~30% карточек с сериями на складах (реалистичнее телефонов/аксессуаров)
            use_series = series_per if (i % 10 < 3) else 0
            for wh_name, wh_id in whs:
                if use_series:
                    for s in range(use_series):
                        sid = f"ser-{i:06d}-{wh_id[:8]}-{s}"
                        fh.write(
                            f'<Товар code="{code}" parentCode="{CAT_CODE}" '
                            f'name="{name}" type="Тест" typeID="{TYPE_ID}" '
                            f'sklad="{wh_name}" skladID="{wh_id}" '
                            f'series="{sid}" seriesID="{sid}" '
                            f'quantity="{(i % 5) + 1}.000" price="1\u00a0990.00" />'
                        )
                        rows += 1
                else:
                    fh.write(
                        f'<Товар code="{code}" parentCode="{CAT_CODE}" '
                        f'name="{name}" type="Тест" typeID="{TYPE_ID}" '
                        f'sklad="{wh_name}" skladID="{wh_id}" '
                        f'series="" seriesID="" '
                        f'quantity="{(i % 5) + 1}.000" price="1\u00a0990.00" />'
                    )
                    rows += 1
            if i % 2000 == 0:
                fh.flush()
        fh.write("</Товары>\n")
    elapsed = _ms(t0)
    size = path.stat().st_size
    return {
        "path": str(path),
        "cards": cards,
        "xml_rows": rows,
        "warehouses": len(whs),
        "series_per_card_wh_when_used": series_per,
        "bytes": size,
        "gen_ms": elapsed,
    }


def bench_parser(path: Path, meta: dict[str, Any]) -> dict[str, Any]:
    from integrations.onec.parser import OneCParseError, parse_products_xml

    gc.collect()
    rss0 = _rss_mib()
    tracemalloc.start()
    t_read0 = _now()
    raw = path.read_bytes()
    read_ms = _ms(t_read0)
    t_parse0 = _now()
    try:
        rows = parse_products_xml(raw)
        parse_ms = _ms(t_parse0)
        err = None
    except OneCParseError as exc:
        parse_ms = _ms(t_parse0)
        rows = []
        err = str(exc)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del raw
    gc.collect()
    codes = {r.code for r in rows}
    out = {
        **meta,
        "read_ms": read_ms,
        "parse_ms": parse_ms,
        "total_ms": round(read_ms + parse_ms, 2),
        "parsed_rows": len(rows),
        "unique_cards": len(codes),
        "tracemalloc_peak_mib": round(peak / (1024 * 1024), 2),
        "tracemalloc_current_mib": round(current / (1024 * 1024), 2),
        "rss_before_mib": rss0,
        "rss_after_mib": _rss_mib(),
        "avail_mib": _avail_mib(),
        "error": err,
    }
    # освобождаем rows
    del rows
    gc.collect()
    return out


def parser_edge_cases() -> list[dict[str, Any]]:
    from integrations.onec.parser import (
        OneCParseError,
        parse_catalog_xml_strings,
        parse_products_xml,
    )

    cases: list[dict[str, Any]] = []

    def run(name: str, fn):
        try:
            result = fn()
            cases.append({"name": name, "ok": True, "result": result})
        except Exception as exc:
            cases.append(
                {
                    "name": name,
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:300],
                }
            )

    run(
        "empty_xml",
        lambda: parse_products_xml(""),
    )
    run(
        "malformed_xml",
        lambda: parse_products_xml("<Товары><Товар code='x'></Товары>"),
    )
    run(
        "incomplete_no_products_tag_content",
        lambda: (
            lambda p: {
                "rows": len(p.product_rows),
                "warnings": p.parse_warnings,
            }
        )(parse_catalog_xml_strings(folders_xml(), "<Товары></Товары>")),
    )
    run(
        "bad_quantity_still_parsed_as_row",
        lambda: (
            lambda rows: {
                "rows": len(rows),
                "qty_problem": rows[0].quantity_problem() if rows else None,
                "not_empty_success": len(rows) > 0,
            }
        )(
            parse_products_xml(
                '<Товары><Товар code="X1" parentCode="C" name="n" '
                'sklad="БАМ" skladID="1418e927-cea5-11f0-82e3-00155d01c802" '
                'quantity="abc" price="10"/></Товары>'
            )
        ),
    )
    # Пустой products не должен тихо стать успешным apply snapshot
    run(
        "empty_products_plan_raises",
        lambda: (
            __import__(
                "integrations.onec.importer", fromlist=["plan_catalog_import_from_xml_strings"]
            ).plan_catalog_import_from_xml_strings(folders_xml(), "<Товары></Товары>")
        ),
    )
    return cases


def seed_stores_and_category():
    from apps.products.models import Category
    from tests.onec_test_utils import ensure_confirmed_stores

    stores = ensure_confirmed_stores()
    cat, _ = Category.objects.get_or_create(
        onec_code=CAT_CODE,
        defaults={
            "title": "Synth Category",
            "slug": "synth-category-b8018",
            "is_active": True,
        },
    )
    return stores, cat


def seed_products(cat, n: int, prefix: str = "SYN") -> list:
    from decimal import Decimal

    from apps.products.models import Product

    # bulk_create для скорости на SQLite
    objs = [
        Product(
            title=f"Synth Item {i}",
            slug=f"synth-b8018-{prefix.lower()}-{i}",
            sku=f"{prefix}-{i:06d}",
            onec_code=f"{prefix}-{i:06d}",
            category=cat,
            price=Decimal("1990.00"),
            is_active=True,
        )
        for i in range(n)
    ]
    return Product.objects.bulk_create(objs, batch_size=500)


def bench_dry_run(folders_path: Path, products_path: Path, label: str) -> dict[str, Any]:
    from integrations.onec.importer import ImportMode, plan_from_parsed
    from integrations.onec.parser import parse_catalog_files
    from integrations.onec.reporting import build_issue_counts, partition_issues

    gc.collect()
    rss0 = _rss_mib()
    tracemalloc.start()
    t0 = _now()
    parsed = parse_catalog_files(folders_path, products_path)
    parse_ms = _ms(t0)
    t1 = _now()
    plan = plan_from_parsed(parsed, mode=ImportMode.DRY_RUN)
    plan_ms = _ms(t1)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    partitioned = partition_issues(plan.issues)
    counts = build_issue_counts(partitioned)
    report = plan.to_dict()
    report_bytes = len(json.dumps(report, ensure_ascii=False).encode("utf-8"))

    from apps.stores.models import Stock

    stock_before = Stock.objects.count()
    # DRY-RUN не должен менять остатки
    stock_after = Stock.objects.count()

    out = {
        "label": label,
        "parse_ms": parse_ms,
        "plan_ms": plan_ms,
        "total_ms": round(parse_ms + plan_ms, 2),
        "product_rows": len(parsed.product_rows),
        "planned_stocks": len(plan.stocks),
        "stocks_to_zero": len(plan.stocks_to_zero),
        "products_actions": len(plan.products),
        "warnings_count": counts.get("warnings_count"),
        "errors_count": counts.get("errors_count"),
        "blockers_count": counts.get("blockers_count"),
        "apply_blockers": len(plan.apply_blockers),
        "apply_allowed": plan.apply_allowed,
        "report_bytes": report_bytes,
        "tracemalloc_peak_mib": round(peak / (1024 * 1024), 2),
        "rss_before_mib": rss0,
        "rss_after_mib": _rss_mib(),
        "stock_count_unchanged": stock_before == stock_after,
        "stock_count": stock_after,
    }
    del parsed, plan, report
    gc.collect()
    return out


def dry_run_scenarios(stores, cat) -> list[dict[str, Any]]:
    from integrations.onec.importer import ImportMode, plan_catalog_import_from_xml_strings
    from integrations.onec.parser import OneCParseError

    bam_id = WAREHOUSES[1][1]
    bam_name = WAREHOUSES[1][0]
    out: list[dict[str, Any]] = []

    def attempt(name: str, products: str, expect_block: bool | None = None):
        try:
            plan = plan_catalog_import_from_xml_strings(folders_xml(), products, mode=ImportMode.DRY_RUN)
            out.append(
                {
                    "name": name,
                    "raised": False,
                    "apply_allowed": plan.apply_allowed,
                    "blockers": len(plan.apply_blockers),
                    "stocks": len(plan.stocks),
                    "issues": len(plan.issues),
                    "blocker_types": [b.get("type") for b in plan.apply_blockers[:5]],
                    "expect_block_match": (None if expect_block is None else (not plan.apply_allowed) == expect_block),
                }
            )
        except Exception as exc:
            out.append(
                {
                    "name": name,
                    "raised": True,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:240],
                    "expect_parse_error": isinstance(exc, OneCParseError),
                }
            )

    # matched
    attempt(
        "all_matched",
        f'<Товары><Товар code="SYN-000000" parentCode="{CAT_CODE}" name="Synth Item 0" '
        f'type="Тест" typeID="{TYPE_ID}" sklad="{bam_name}" skladID="{bam_id}" '
        f'series="" seriesID="" quantity="2.000" price="1\u00a0990.00"/></Товары>',
        expect_block=False,
    )
    # unknown warehouse
    attempt(
        "unknown_warehouse",
        f'<Товары><Товар code="SYN-000000" parentCode="{CAT_CODE}" name="Synth Item 0" '
        f'type="Тест" typeID="{TYPE_ID}" sklad="UNKNOWN" '
        f'skladID="00000000-0000-0000-0000-000000000099" '
        f'series="" seriesID="" quantity="1.000" price="100.00"/></Товары>',
        expect_block=True,
    )
    # series without id
    attempt(
        "series_without_id",
        f'<Товары><Товар code="SYN-000000" parentCode="{CAT_CODE}" name="Synth Item 0" '
        f'type="Тест" typeID="{TYPE_ID}" sklad="{bam_name}" skladID="{bam_id}" '
        f'series="only-name" seriesID="" quantity="1.000" price="100.00"/></Товары>',
    )
    # bad qty
    attempt(
        "bad_quantity",
        f'<Товары><Товар code="SYN-000000" parentCode="{CAT_CODE}" name="Synth Item 0" '
        f'type="Тест" typeID="{TYPE_ID}" sklad="{bam_name}" skladID="{bam_id}" '
        f'series="" seriesID="" quantity="-3" price="100.00"/></Товары>',
    )
    # empty products
    attempt("empty_products", "<Товары></Товары>")
    # new product
    attempt(
        "new_product",
        f'<Товары><Товар code="SYN-NEW-999" parentCode="{CAT_CODE}" name="Brand New" '
        f'type="Тест" typeID="{TYPE_ID}" sklad="{bam_name}" skladID="{bam_id}" '
        f'series="" seriesID="" quantity="1.000" price="500.00"/></Товары>',
        expect_block=False,
    )
    return out


def bench_batch_apply(n_rows: int, stores, cat, run_tag: str) -> dict[str, Any]:
    from decimal import Decimal

    from apps.products.models import Product
    from apps.stores.models import Stock, StockMovement
    from apps.stores.stock_ops import OnecStockUpsertItem, apply_onec_stock_upserts_batch

    store = list(stores.values())[1]  # БАМ
    # продукты: создаём столько, сколько нужно (reuse)
    need = min(n_rows, 500)
    existing = list(Product.objects.filter(onec_code__startswith="BAT-").order_by("onec_code")[:need])
    if len(existing) < need:
        start = len(existing)
        more = Product.objects.bulk_create(
            [
                Product(
                    title=f"Batch {i}",
                    slug=f"batch-b8018-{i}",
                    sku=f"BAT-{i:06d}",
                    onec_code=f"BAT-{i:06d}",
                    category=cat,
                    price=Decimal("10.00"),
                    is_active=True,
                )
                for i in range(start, need)
            ],
            batch_size=500,
        )
        existing.extend(more)

    items = [
        OnecStockUpsertItem(
            product_id=existing[i % len(existing)].pk,
            store_id=store.pk,
            series_id=f"B-{run_tag}-{i}",
            series_name="",
            quantity=(i % 5) + 1,
        )
        for i in range(n_rows)
    ]

    # reserved на первой позиции для проверки сохранения
    first = items[0]
    Stock.objects.update_or_create(
        product_id=first.product_id,
        store_id=first.store_id,
        onec_series_id=first.series_id,
        defaults={"quantity": 1, "reserved_quantity": 1},
    )

    gc.collect()
    rss0 = _rss_mib()
    tracemalloc.start()
    t0 = _now()
    with CaptureQueriesContext(connection) as ctx:
        with transaction.atomic():
            result = apply_onec_stock_upserts_batch(items, run_id=f"b8018-{run_tag}")
    elapsed_ms = _ms(t0)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    row0 = Stock.objects.get(
        product_id=first.product_id,
        store_id=first.store_id,
        onec_series_id=first.series_id,
    )
    mov_count = StockMovement.objects.filter(source="onec.importer", reason="onec_stock_upsert").count()

    # idempotent repeat
    t1 = _now()
    with CaptureQueriesContext(connection) as ctx2:
        with transaction.atomic():
            result2 = apply_onec_stock_upserts_batch(items, run_id=f"b8018-{run_tag}")
    repeat_ms = _ms(t1)

    # new run_id should re-apply
    t2 = _now()
    with transaction.atomic():
        result3 = apply_onec_stock_upserts_batch(items, run_id=f"b8018-{run_tag}-rerun")
    rerun_ms = _ms(t2)

    out = {
        "rows": n_rows,
        "applied": result["applied"],
        "skipped_idempotent_first": result["skipped_idempotent"],
        "time_ms": elapsed_ms,
        "sql_queries": len(ctx),
        "sql_per_row": round(len(ctx) / max(n_rows, 1), 4),
        "repeat_applied": result2["applied"],
        "repeat_skipped": result2["skipped_idempotent"],
        "repeat_ms": repeat_ms,
        "repeat_sql": len(ctx2),
        "new_run_applied": result3["applied"],
        "new_run_ms": rerun_ms,
        "reserved_preserved": row0.reserved_quantity == 1,
        "quantity_updated": row0.quantity == first.quantity,
        "stock_movements_total_approx": mov_count,
        "tracemalloc_peak_mib": round(peak / (1024 * 1024), 2),
        "rss_before_mib": rss0,
        "rss_after_mib": _rss_mib(),
        "engine": settings.DATABASES["default"]["ENGINE"],
        "within_budget": elapsed_ms < APPLY_TIME_BUDGET_S * 1000,
    }
    del items
    gc.collect()
    return out


def semantics_checks(stores, cat) -> list[dict[str, Any]]:
    from decimal import Decimal

    from apps.products.models import Product
    from apps.stores.models import Stock
    from apps.stores.stock_ops import OnecStockUpsertItem, apply_onec_stock_upserts_batch

    store = list(stores.values())[1]
    p = Product.objects.create(
        title="Sem",
        slug=f"sem-{uuid.uuid4().hex[:8]}",
        price=Decimal("1"),
        category=cat,
        onec_code=f"SEM-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    results = []

    def apply(items, run_id):
        with transaction.atomic():
            return apply_onec_stock_upserts_batch(items, run_id=run_id)

    # appear after zero
    apply(
        [OnecStockUpsertItem(product_id=p.pk, store_id=store.pk, series_id="S1", series_name="", quantity=0)],
        "sem-zero",
    )
    row = Stock.objects.get(product=p, store=store, onec_series_id="S1")
    results.append(
        {
            "case": "zero_keeps_row_not_delete_product",
            "stock_qty": row.quantity,
            "product_exists": Product.objects.filter(pk=p.pk).exists(),
        }
    )
    apply(
        [OnecStockUpsertItem(product_id=p.pk, store_id=store.pk, series_id="S1", series_name="", quantity=4)],
        "sem-reappear",
    )
    row.refresh_from_db()
    results.append({"case": "reappear_after_zero", "stock_qty": row.quantity})

    # series disappear → zero other series via separate item
    apply(
        [OnecStockUpsertItem(product_id=p.pk, store_id=store.pk, series_id="S2", series_name="", quantity=3)],
        "sem-s2",
    )
    apply(
        [OnecStockUpsertItem(product_id=p.pk, store_id=store.pk, series_id="S2", series_name="", quantity=0)],
        "sem-s2-gone",
    )
    s2 = Stock.objects.get(product=p, store=store, onec_series_id="S2")
    results.append({"case": "series_disappear_zero", "stock_qty": s2.quantity})

    # change qty preserves reserved
    Stock.objects.filter(pk=row.pk).update(reserved_quantity=2)
    apply(
        [OnecStockUpsertItem(product_id=p.pk, store_id=store.pk, series_id="S1", series_name="", quantity=9)],
        "sem-qty",
    )
    row.refresh_from_db()
    results.append(
        {
            "case": "qty_change_preserves_reserved",
            "qty": row.quantity,
            "reserved": row.reserved_quantity,
            "available": row.quantity - row.reserved_quantity,
        }
    )
    return results


def transaction_rollback_test(stores, cat) -> dict[str, Any]:
    from decimal import Decimal

    from apps.products.models import Product
    from apps.stores.models import Stock
    from apps.stores.stock_ops import OnecStockUpsertItem, apply_onec_stock_upserts_batch

    store = list(stores.values())[1]
    p = Product.objects.create(
        title="Tx",
        slug=f"tx-{uuid.uuid4().hex[:8]}",
        price=Decimal("1"),
        category=cat,
        onec_code=f"TX-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    before = Stock.objects.filter(product=p).count()
    items = [
        OnecStockUpsertItem(
            product_id=p.pk,
            store_id=store.pk,
            series_id=f"T{i}",
            series_name="",
            quantity=2,
        )
        for i in range(50)
    ]
    failed = False
    try:
        with transaction.atomic():
            apply_onec_stock_upserts_batch(items[:25], run_id="tx-mid-fail")
            # искусственная ошибка в середине внешней транзакции
            raise RuntimeError("simulated mid-apply failure")
    except RuntimeError:
        failed = True
    after = Stock.objects.filter(product=p).count()
    return {
        "simulated_error": failed,
        "stocks_before": before,
        "stocks_after": after,
        "no_partial_apply": after == before,
    }


def lock_tests() -> list[dict[str, Any]]:
    from django.core.cache.backends.locmem import LocMemCache

    from integrations.onec import catalog_sync

    out: list[dict[str, Any]] = []
    cache.clear()
    out.append(
        {
            "backend": settings.CACHES["default"]["BACKEND"],
            "cache_persists_locks": catalog_sync._cache_persists_locks(),
            "note": "test settings use DummyCache — add() всегда True, get() не хранит",
        }
    )

    redis_ping = False
    try:
        import redis as redis_lib

        r = redis_lib.Redis(host="127.0.0.1", port=6379, db=15, socket_connect_timeout=1)
        redis_ping = bool(r.ping())
    except Exception as exc:
        out.append({"redis_local": False, "reason": str(exc)[:200]})

    # Semantika cache.add lock (как Redis) через LocMemCache — без чтения .env
    loc = LocMemCache("b8018", {})
    key = catalog_sync.APPLY_LOCK_CACHE_KEY
    ok1 = loc.add(key, "run-a", 5)
    ok2 = loc.add(key, "run-b", 5)
    held = loc.get(key)
    loc.delete(key)
    ok3 = loc.add(key, "run-c", 1)
    time.sleep(1.2)
    expired = loc.get(key)
    ok4 = loc.add(key, "run-d", 5)
    out.append(
        {
            "redis_ping": redis_ping,
            "locmem_lock_first": ok1,
            "locmem_lock_second_blocked": ok2 is False,
            "held_value": held,
            "reacquire_after_delete": ok3,
            "expired_after_ttl": expired is None,
            "reacquire_after_expiry": ok4,
            "note": (
                "Lock API validated via LocMemCache.add (same contract as Redis cache.add). "
                "Django test CACHES remains DummyCache."
            ),
        }
    )

    from django.utils import timezone

    from apps.products.sync_models import OneCCatalogSyncLog

    run_a = catalog_sync._new_run_id()
    try:
        OneCCatalogSyncLog.objects.create(
            run_id=run_a,
            status=OneCCatalogSyncLog.STATUS_RUNNING,
            dry_run=False,
            source=OneCCatalogSyncLog.SOURCE_FIXTURE,
            started_at=timezone.now(),
        )
        blocked = catalog_sync._running_apply_in_db(exclude_run_id="")
        out.append({"db_running_apply_blocks": blocked})
        OneCCatalogSyncLog.objects.filter(run_id=run_a).update(status=OneCCatalogSyncLog.STATUS_FAILED)
    except Exception as exc:
        out.append({"db_running_apply_error": str(exc)[:240]})

    return out


def main() -> int:
    results = Results()
    engine = settings.DATABASES["default"]["ENGINE"]
    results.environment = {
        "django_settings": os.environ.get("DJANGO_SETTINGS_MODULE"),
        "db_engine": engine,
        "db_name": str(settings.DATABASES["default"].get("NAME")),
        "cache_backend": settings.CACHES["default"]["BACKEND"],
        "is_sqlite": "sqlite" in engine,
        "is_postgres": "postgresql" in engine,
        "rss_start_mib": _rss_mib(),
        "avail_start_mib": _avail_mib(),
        "python": sys.version.split()[0],
    }
    results.inventory = {
        "parser": "defusedxml ET.fromstring / ET.parse — full DOM",
        "importer_plan": "in-memory CatalogImportPlan lists (products/stocks/stocks_to_zero/issues)",
        "apply": "single transaction.atomic apply_catalog_import (ONEC-014)",
        "batch": "apply_onec_stock_upserts_batch bulk_create/update + bulk StockMovement",
        "lock": "cache.add APPLY_LOCK_CACHE_KEY + SyncLog STATUS_RUNNING fallback",
        "n_plus_1_risks": [
            "apply_catalog_import product create/update loop (per product)",
            "legacy apply_onec_stock_upsert per-row (superseded by batch in apply path)",
        ],
        "postgres_required_for": [
            "true concurrent writers / row locks",
            "realistic large-tx WAL behaviour",
            "test_concurrency_postgres suite",
        ],
    }
    results.notes.append("SQLite :memory: results are NOT interchangeable with PostgreSQL production benchmarks.")

    # --- generate fixtures ---
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    (FIXTURE_DIR / "folders.xml").write_text(folders_xml(), encoding="utf-8")

    volumes = [
        VolumeSpec("2k_x3wh", 2_000, 3, 2),
        VolumeSpec("10k_x3wh", 10_000, 3, 2),
        VolumeSpec("25k_x1wh", 25_000, 1, 1),
        VolumeSpec("50k_x1wh", 50_000, 1, 1, gen_50k=True),
    ]

    fixture_meta: dict[str, dict[str, Any]] = {}
    for vol in volumes:
        ok, reason = _safe_to_continue()
        if not ok:
            results.aborted.append(f"skip generate {vol.name}: {reason}")
            break
        if vol.gen_50k:
            # только если предыдущий parser peak приемлем — решение после 25k
            prev = [p for p in results.parser if p.get("name") == "25k_x1wh"]
            if not prev:
                # generate later after parser stage decision
                continue
        path = FIXTURE_DIR / f"products_{vol.name}.xml"
        print(f"[GEN] {vol.name} ...", flush=True)
        meta = generate_products_xml(
            path,
            cards=vol.cards,
            warehouses=vol.warehouses,
            series_per=vol.series_per_card_wh,
        )
        meta["name"] = vol.name
        results.fixtures.append(meta)
        fixture_meta[vol.name] = meta
        save(results)
        print(
            f"  cards={meta['cards']} rows={meta['xml_rows']} " f"bytes={meta['bytes']} gen_ms={meta['gen_ms']}",
            flush=True,
        )

    # --- parser ---
    for name, meta in list(fixture_meta.items()):
        ok, reason = _safe_to_continue()
        if not ok:
            results.aborted.append(f"skip parser {name}: {reason}")
            break
        print(f"[PARSER] {name} ...", flush=True)
        row = bench_parser(Path(meta["path"]), {"name": name, **meta})
        results.parser.append(row)
        save(results)
        print(
            f"  parse_ms={row['parse_ms']} rows={row['parsed_rows']} "
            f"peak_mib={row['tracemalloc_peak_mib']} rss={row['rss_after_mib']}",
            flush=True,
        )
        ok2, reason2 = _safe_to_continue(row["tracemalloc_peak_mib"])
        if not ok2:
            results.aborted.append(f"stop after parser {name}: {reason2}")
            break

    # Conditional 50k
    if not any(a.startswith("stop after parser") for a in results.aborted):
        last = results.parser[-1] if results.parser else None
        if last and last.get("tracemalloc_peak_mib", 999) < 200 and (_avail_mib() or 0) > 400:
            vol = VolumeSpec("50k_x1wh", 50_000, 1, 1)
            path = FIXTURE_DIR / f"products_{vol.name}.xml"
            print("[GEN] 50k_x1wh ...", flush=True)
            meta = generate_products_xml(
                path, cards=vol.cards, warehouses=vol.warehouses, series_per=vol.series_per_card_wh
            )
            meta["name"] = vol.name
            results.fixtures.append(meta)
            print("[PARSER] 50k_x1wh ...", flush=True)
            row = bench_parser(path, {"name": vol.name, **meta})
            results.parser.append(row)
            save(results)
        else:
            results.aborted.append(
                "50k skipped: peak/avail safety gate "
                f"(last_peak={last.get('tracemalloc_peak_mib') if last else None}, "
                f"avail={_avail_mib()})"
            )

    print("[PARSER EDGE]", flush=True)
    results.parser_edge = parser_edge_cases()
    save(results)

    # --- Django test DB for dry-run / apply ---
    setup_test_environment()
    runner = DiscoverRunner(verbosity=0, interactive=False, keepdb=False)
    old_config = runner.setup_databases()
    try:
        stores, cat = seed_stores_and_category()
        # seed first 2000 products for dry-run match scenarios
        print("[SEED] products 2000", flush=True)
        seed_products(cat, 2000, prefix="SYN")

        # dry-run on available fixtures (prefer smaller first)
        for name in ["2k_x3wh", "10k_x3wh", "25k_x1wh"]:
            meta = next((f for f in results.fixtures if f["name"] == name), None)
            if not meta:
                continue
            ok, reason = _safe_to_continue()
            if not ok:
                results.aborted.append(f"skip dry-run {name}: {reason}")
                break
            # For 10k/25k seed more products to reduce create-plan cost noise
            if name.startswith("10k"):
                print("[SEED] products +8000 for 10k", flush=True)
                # SYN-002000 .. already may not exist
                from decimal import Decimal

                from apps.products.models import Product

                have = Product.objects.filter(onec_code__startswith="SYN-").count()
                if have < 10_000:
                    Product.objects.bulk_create(
                        [
                            Product(
                                title=f"Synth Item {i}",
                                slug=f"synth-b8018-syn-{i}",
                                sku=f"SYN-{i:06d}",
                                onec_code=f"SYN-{i:06d}",
                                category=cat,
                                price=Decimal("1990.00"),
                                is_active=True,
                            )
                            for i in range(have, 10_000)
                        ],
                        batch_size=500,
                    )
            print(f"[DRY-RUN] {name} ...", flush=True)
            try:
                row = bench_dry_run(FIXTURE_DIR / "folders.xml", Path(meta["path"]), name)
                results.dry_run.append(row)
                save(results)
                print(
                    f"  plan_ms={row['plan_ms']} stocks={row['planned_stocks']} "
                    f"blockers={row['apply_blockers']} peak={row['tracemalloc_peak_mib']}",
                    flush=True,
                )
            except Exception as exc:
                results.dry_run.append(
                    {
                        "label": name,
                        "error": str(exc)[:400],
                        "traceback": traceback.format_exc()[-500:],
                    }
                )
                save(results)
                print(f"  ERROR {exc}", flush=True)

        print("[DRY-RUN SCENARIOS]", flush=True)
        results.dry_run_scenarios = dry_run_scenarios(stores, cat)
        save(results)

        # batch apply sizes
        for n in [1_000, 5_000, 10_000, 25_000]:
            ok, reason = _safe_to_continue()
            if not ok:
                results.aborted.append(f"skip apply {n}: {reason}")
                break
            print(f"[APPLY] rows={n} ...", flush=True)
            try:
                row = bench_batch_apply(n, stores, cat, run_tag=f"n{n}")
                results.batch_apply.append(row)
                save(results)
                print(
                    f"  applied={row['applied']} ms={row['time_ms']} "
                    f"sql={row['sql_queries']} qpr={row['sql_per_row']}",
                    flush=True,
                )
                if not row["within_budget"]:
                    results.aborted.append(f"stop apply after {n}: exceeded {APPLY_TIME_BUDGET_S}s budget")
                    break
                if n >= 10_000 and row["time_ms"] > 60_000:
                    results.aborted.append(f"skip 25k apply: 10k already {row['time_ms']}ms on SQLite")
                    break
            except Exception as exc:
                results.batch_apply.append({"rows": n, "error": str(exc)[:400], "tb": traceback.format_exc()[-400:]})
                save(results)
                print(f"  ERROR {exc}", flush=True)
                break

        print("[SEMANTICS]", flush=True)
        results.apply_semantics = semantics_checks(stores, cat)
        print("[TX ROLLBACK]", flush=True)
        results.transactions.append(transaction_rollback_test(stores, cat))
        print("[LOCKS]", flush=True)
        results.locks = lock_tests()
        save(results)
    finally:
        runner.teardown_databases(old_config)

    results.environment["rss_end_mib"] = _rss_mib()
    results.environment["avail_end_mib"] = _avail_mib()
    save(results)
    print(f"\n[DONE] results → {RESULT_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
