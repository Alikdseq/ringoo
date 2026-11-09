"""
Targeted YooKassa TEST refund drill for explicitly provided payment UUIDs.

Does NOT scan payment lists. Does NOT invent IDs.
Requires CLI flags and --i-confirm-test-refunds.

Usage (after owner confirmation):
  python backend/scripts/block4_yookassa_targeted_refund_drill.py \\
    --full-payment-id <uuid> --full-amount 10.00 \\
    --partial-payment-id <uuid> --partial-amount 1.00 \\
    --i-confirm-test-refunds

Safety:
  - refuses non-test secrets / YOOKASSA_TEST_MODE!=1
  - refuses missing confirmation flag
  - refuses identical FULL/PARTIAL UUIDs
  - never uses live_ keys
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from urllib import error, request


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Targeted YooKassa TEST refunds")
    p.add_argument("--full-payment-id", required=True)
    p.add_argument("--full-amount", required=True, help="Exact full refund amount, e.g. 10.00")
    p.add_argument("--partial-payment-id", required=True)
    p.add_argument("--partial-amount", required=True, help="Partial refund amount < payment remain")
    p.add_argument(
        "--i-confirm-test-refunds",
        action="store_true",
        help="Required explicit confirmation flag",
    )
    p.add_argument("--dry-run-plan-only", action="store_true", help="Only GET payments, no refunds")
    return p.parse_args()


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    args = parse_args()

    shop = os.environ.get("YOOKASSA_SHOP_ID", "").strip()
    secret = os.environ.get("YOOKASSA_SECRET_KEY", "").strip()
    enabled = os.environ.get("YOOKASSA_ENABLED", "").strip().lower() in ("1", "true", "yes")
    test_mode = os.environ.get("YOOKASSA_TEST_MODE", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    api = os.environ.get("YOOKASSA_API_URL", "https://api.yookassa.ru/v3").rstrip("/")

    print("YK_ENABLED", enabled)
    print("YK_TEST_MODE", test_mode)
    print("YK_SHOP_ID", shop)
    print("YK_SECRET_IS_TEST", secret.startswith("test_"))
    print("FULL_ID", args.full_payment_id)
    print("PARTIAL_ID", args.partial_payment_id)

    if not args.i_confirm_test_refunds and not args.dry_run_plan_only:
        print("BLOCKED: pass --i-confirm-test-refunds or --dry-run-plan-only")
        return 11
    if not enabled or not test_mode or not secret.startswith("test_") or secret.startswith("live_"):
        print("BLOCKED: refusing non-test or disabled config")
        return 12
    if args.full_payment_id.strip() == args.partial_payment_id.strip():
        print("BLOCKED: FULL and PARTIAL must be different payments")
        return 13

    auth = base64.b64encode(f"{shop}:{secret}".encode()).decode()

    def call(method: str, path: str, body: dict | None = None, idem: str | None = None) -> dict:
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        data = None
        if method.upper() in ("POST", "PUT", "PATCH"):
            headers["Idempotence-Key"] = idem or str(uuid.uuid4())
            data = json.dumps(body or {}).encode("utf-8")
        req = request.Request(api + path, data=data, headers=headers, method=method.upper())
        ctx = ssl.create_default_context()
        try:
            with request.urlopen(req, timeout=45, context=ctx) as resp:
                raw = resp.read()
        except error.HTTPError as exc:
            raw = exc.read() if exc.fp else b""
            payload = json.loads(raw.decode("utf-8") or "{}")
            raise RuntimeError(
                f"HTTP {exc.code}: {payload.get('description') or payload.get('code')}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"unreachable: {exc.reason}") from exc
        return json.loads(raw.decode("utf-8") or "{}") if raw else {}

    def remain(payment: dict) -> Decimal:
        amount_val = Decimal(str((payment.get("amount") or {}).get("value") or "0"))
        refunded_val = Decimal(str((payment.get("refunded_amount") or {}).get("value") or "0"))
        return amount_val - refunded_val

    full = call("GET", f"/payments/{args.full_payment_id.strip()}")
    partial = call("GET", f"/payments/{args.partial_payment_id.strip()}")
    print(
        "FULL_STATUS",
        full.get("status"),
        "paid",
        full.get("paid"),
        "amount",
        (full.get("amount") or {}).get("value"),
        "remain",
        remain(full),
        "test",
        full.get("test"),
    )
    print(
        "PARTIAL_STATUS",
        partial.get("status"),
        "paid",
        partial.get("paid"),
        "amount",
        (partial.get("amount") or {}).get("value"),
        "remain",
        remain(partial),
        "test",
        partial.get("test"),
    )

    if args.dry_run_plan_only:
        print("PLAN_ONLY_OK")
        return 0

    if full.get("status") != "succeeded" or not full.get("paid"):
        print("BLOCKED: FULL payment not succeeded")
        return 14
    if partial.get("status") != "succeeded" or not partial.get("paid"):
        print("BLOCKED: PARTIAL payment not succeeded")
        return 15
    if full.get("test") is False or partial.get("test") is False:
        print("BLOCKED: payment marked test=false by YooKassa")
        return 16

    full_amt = Decimal(str(args.full_amount)).quantize(Decimal("0.01"))
    part_amt = Decimal(str(args.partial_amount)).quantize(Decimal("0.01"))
    if full_amt != remain(full):
        print("BLOCKED: --full-amount must equal current remain", remain(full))
        return 17
    if part_amt <= 0 or part_amt >= remain(partial):
        print("BLOCKED: --partial-amount must be >0 and < remain", remain(partial))
        return 18

    # FULL refund
    idem_full = f"ringoo-full-{args.full_payment_id}-{full_amt}"
    r_full = call(
        "POST",
        "/refunds",
        {
            "payment_id": args.full_payment_id.strip(),
            "amount": {"value": f"{full_amt:.2f}", "currency": "RUB"},
        },
        idem=idem_full,
    )
    print("FULL_REFUND", r_full.get("id"), r_full.get("status"), (r_full.get("amount") or {}).get("value"))
    r_full_replay = call(
        "POST",
        "/refunds",
        {
            "payment_id": args.full_payment_id.strip(),
            "amount": {"value": f"{full_amt:.2f}", "currency": "RUB"},
        },
        idem=idem_full,
    )
    print("FULL_IDEMPOTENT", r_full_replay.get("id") == r_full.get("id"))

    # PARTIAL refund
    idem_part = f"ringoo-partial-{args.partial_payment_id}-{part_amt}"
    r_part = call(
        "POST",
        "/refunds",
        {
            "payment_id": args.partial_payment_id.strip(),
            "amount": {"value": f"{part_amt:.2f}", "currency": "RUB"},
        },
        idem=idem_part,
    )
    print(
        "PARTIAL_REFUND",
        r_part.get("id"),
        r_part.get("status"),
        (r_part.get("amount") or {}).get("value"),
    )
    r_part_replay = call(
        "POST",
        "/refunds",
        {
            "payment_id": args.partial_payment_id.strip(),
            "amount": {"value": f"{part_amt:.2f}", "currency": "RUB"},
        },
        idem=idem_part,
    )
    print("PARTIAL_IDEMPOTENT", r_part_replay.get("id") == r_part.get("id"))

    # over-refund on PARTIAL must fail
    try:
        call(
            "POST",
            "/refunds",
            {
                "payment_id": args.partial_payment_id.strip(),
                "amount": {
                    "value": f"{(remain(call('GET', f'/payments/{args.partial_payment_id.strip()}')) + Decimal('0.01')):.2f}",
                    "currency": "RUB",
                },
            },
            idem=f"ringoo-over-{args.partial_payment_id}",
        )
        print("OVER_REFUND_UNEXPECTED_OK")
        return 19
    except Exception as exc:
        print("OVER_REFUND_REJECTED", str(exc)[:200])

    print("TARGETED_REFUND_DRILL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
