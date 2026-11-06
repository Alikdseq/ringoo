"""
Standalone YooKassa TEST API refund drill (no Django settings dependency).
Reads credentials from environment only. Refuses non-test secrets.
"""
from __future__ import annotations

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


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
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
    if not enabled or not test_mode or not secret.startswith("test_"):
        print("BLOCKED: refusing non-test or disabled config")
        return 11

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

    # connectivity probe via list
    try:
        listed = call("GET", "/payments?limit=20")
    except Exception as exc:
        print("API_REACHABILITY_FAIL", str(exc)[:200])
        return 12
    items = listed.get("items") or []
    print("LIST_PAYMENTS", len(items))

    pid = ""
    remain = Decimal("0")
    for item in items:
        if str(item.get("status")) != "succeeded" or not item.get("paid"):
            continue
        amount_val = Decimal(str((item.get("amount") or {}).get("value") or "0"))
        refunded_val = Decimal(str((item.get("refunded_amount") or {}).get("value") or "0"))
        rem = amount_val - refunded_val
        if rem >= Decimal("2.00"):
            pid = str(item.get("id"))
            remain = rem
            print("REUSE_PAYMENT", pid, "remain", remain)
            break

    if not pid:
        payment = call(
            "POST",
            "/payments",
            {
                "amount": {"value": "10.00", "currency": "RUB"},
                "capture": True,
                "description": "Ringoo Block4 TEST refund drill",
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://example.com/return",
                },
                "metadata": {"purpose": "block4_refund_drill"},
            },
            idem=f"block4-pay-{uuid.uuid4()}",
        )
        pid = str(payment.get("id"))
        print("CREATED_PAYMENT", pid, "status", payment.get("status"))
        if payment.get("status") != "succeeded":
            print(
                "BLOCKED: created payment needs browser test-card confirmation; "
                "API connectivity VERIFIED with test credentials"
            )
            print("CONFIRMATION", bool((payment.get("confirmation") or {}).get("confirmation_url")))
            return 13

    payment = call("GET", f"/payments/{pid}")
    amount_val = Decimal(str((payment.get("amount") or {}).get("value") or "0"))
    refunded_val = Decimal(str((payment.get("refunded_amount") or {}).get("value") or "0"))
    remain = amount_val - refunded_val
    print("PAYMENT_READY", pid, "remain", remain)
    if remain < Decimal("2.00"):
        print("BLOCKED: insufficient remainder")
        return 14

    part = Decimal("1.00")
    rest = (remain - part).quantize(Decimal("0.01"))
    idem1 = f"block4-ref-partial-{pid}-{part}"
    r1 = call(
        "POST",
        "/refunds",
        {"payment_id": pid, "amount": {"value": f"{part:.2f}", "currency": "RUB"}},
        idem=idem1,
    )
    print("REFUND1", r1.get("id"), r1.get("status"), (r1.get("amount") or {}).get("value"))
    r1b = call(
        "POST",
        "/refunds",
        {"payment_id": pid, "amount": {"value": f"{part:.2f}", "currency": "RUB"}},
        idem=idem1,
    )
    print("REFUND1_IDEMPOTENT", r1b.get("id") == r1.get("id"))

    if rest >= Decimal("0.01"):
        r2 = call(
            "POST",
            "/refunds",
            {"payment_id": pid, "amount": {"value": f"{rest:.2f}", "currency": "RUB"}},
            idem=f"block4-ref-rest-{pid}-{rest}",
        )
        print("REFUND2", r2.get("id"), r2.get("status"), (r2.get("amount") or {}).get("value"))

    try:
        call(
            "POST",
            "/refunds",
            {"payment_id": pid, "amount": {"value": "0.01", "currency": "RUB"}},
            idem=f"block4-over-{pid}",
        )
        print("OVER_REFUND_UNEXPECTED_OK")
        return 16
    except Exception as exc:
        print("OVER_REFUND_REJECTED", str(exc)[:200])

    g1 = call("GET", f"/refunds/{r1.get('id')}")
    print("GET_REFUND1", g1.get("status"), (g1.get("amount") or {}).get("value"))
    print("YK_REFUND_DRILL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
