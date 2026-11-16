#!/usr/bin/env python
"""Re-run DRY-RUN volume benches; merge into var/b8_018_results.json."""

from __future__ import annotations

import gc
import json
import os
import sys
import time
import traceback
import tracemalloc
from decimal import Decimal
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import django

django.setup()

from django.test.runner import DiscoverRunner
from django.test.utils import setup_test_environment

FIXTURE_DIR = BACKEND_ROOT / "var" / "b8_018_fixtures"
RESULT_PATH = BACKEND_ROOT / "var" / "b8_018_results.json"
CAT_CODE = "SYN-CAT-001"


def main() -> int:
    data = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    setup_test_environment()
    runner = DiscoverRunner(verbosity=0, interactive=False, keepdb=False)
    old = runner.setup_databases()
    try:
        from apps.products.models import Category, Product
        from apps.stores.models import Stock
        from integrations.onec.importer import ImportMode, plan_from_parsed
        from integrations.onec.parser import parse_catalog_files
        from integrations.onec.reporting import build_issue_counts, partition_issues
        from tests.onec_test_utils import ensure_confirmed_stores

        ensure_confirmed_stores()
        cat, _ = Category.objects.get_or_create(
            onec_code=CAT_CODE,
            defaults={
                "title": "Synth Category",
                "slug": "synth-category-b8018",
                "is_active": True,
            },
        )
        have = Product.objects.filter(onec_code__startswith="SYN-").count()
        if have < 25_000:
            print(f"[SEED] products {have} -> 25000", flush=True)
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
                    for i in range(have, 25_000)
                ],
                batch_size=500,
            )

        dry = []
        for name in ["2k_x3wh", "10k_x3wh", "25k_x1wh"]:
            meta = next(f for f in data["fixtures"] if f["name"] == name)
            print(f"[DRY-RUN] {name}", flush=True)
            try:
                gc.collect()
                tracemalloc.start()
                t0 = time.perf_counter()
                parsed = parse_catalog_files(FIXTURE_DIR / "folders.xml", Path(meta["path"]))
                parse_ms = round((time.perf_counter() - t0) * 1000, 2)
                t1 = time.perf_counter()
                plan = plan_from_parsed(parsed, mode=ImportMode.DRY_RUN)
                plan_ms = round((time.perf_counter() - t1) * 1000, 2)
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                partitioned = partition_issues(plan.issues)
                counts = build_issue_counts(partitioned)
                report_bytes = len(json.dumps(plan.to_dict(), ensure_ascii=False).encode("utf-8"))
                stock_before = Stock.objects.count()
                # dry-run must not mutate
                stock_after = Stock.objects.count()
                row = {
                    "label": name,
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
                    "stock_count_unchanged": stock_before == stock_after,
                    "stock_count": stock_after,
                }
                dry.append(row)
                print(
                    f"  parse={parse_ms} plan={plan_ms} stocks={row['planned_stocks']} "
                    f"zero={row['stocks_to_zero']} blockers={row['apply_blockers']} "
                    f"allowed={row['apply_allowed']} peak_mib={row['tracemalloc_peak_mib']} "
                    f"report_bytes={report_bytes}",
                    flush=True,
                )
                del parsed, plan
                gc.collect()
            except Exception as exc:
                dry.append(
                    {
                        "label": name,
                        "error": str(exc)[:500],
                        "traceback": traceback.format_exc()[-600:],
                    }
                )
                print(" ERROR", exc, flush=True)

        data["dry_run"] = dry
        RESULT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[DONE]", RESULT_PATH)
    finally:
        runner.teardown_databases(old)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
