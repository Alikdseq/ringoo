"""
Real YooKassa TEST-API refund drill.
Requires YOOKASSA_* with test_ secret key. Never uses live keys.
Creates a test payment (embedded method), waits until succeeded if possible,
creates full + partial refunds via API, checks idempotency.
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from decimal import Decimal
from pathlib import Path

# Load root .env into os.environ without printing secrets
ROOT = Path(__file__).resolve().parents[2]
for env_file in (ROOT / ".env", Path("/app/.env"), Path(".env")):
    if not env_file.exists():
        continue
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
os.environ["YOOKASSA_ENABLED"] = os.environ.get("YOOKASSA_ENABLED", "1")

import django

django.setup()

from django.conf import settings
from integrations.yookassa.client import YooKassaClient, YooKassaError


def mask(s: str) -> str:
    s = s or ""
    if len(s) <= 8:
        return "***"
    return s[:4] + "…" + s[-2:]


def main() -> int:
    shop = str(getattr(settings, "YOOKASSA_SHOP_ID", "") or "")
    secret = str(getattr(settings, "YOOKASSA_SECRET_KEY", "") or "")
    test_mode = bool(getattr(settings, "YOOKASSA_TEST_MODE", False))
    enabled = bool(getattr(settings, "YOOKASSA_ENABLED", False))
    print("YK_ENABLED", enabled)
    print("YK_TEST_MODE", test_mode)
    print("YK_SHOP_ID", shop)
    print("YK_SECRET_PREFIX", mask(secret))
    print("YK_SECRET_IS_TEST", secret.startswith("test_"))

    if not enabled:
        print("BLOCKED: YOOKASSA_ENABLED is false")
        return 10
    if not test_mode or not secret.startswith("test_"):
        print("BLOCKED: refusing non-test YooKassa credentials")
        return 11

    client = YooKassaClient()

    # 1) Try reuse an existing succeeded test payment with remaining refundable amount
    pid = ""
    try:
        listed = client._request("GET", "/payments?limit=20")
        items = listed.get("items") or []
        print("LIST_PAYMENTS", len(items))
        for item in items:
            if str(item.get("status")) != "succeeded":
                continue
            if not bool(item.get("paid")):
                continue
            amount_val = Decimal(str((item.get("amount") or {}).get("value") or "0"))
            refunded_val = Decimal(
                str((item.get("refunded_amount") or {}).get("value") or "0")
            )
            remain = amount_val - refunded_val
            if remain >= Decimal("2.00"):
                pid = str(item.get("id") or "")
                print(
                    "REUSE_PAYMENT",
                    pid,
                    "amount",
                    amount_val,
                    "refunded",
                    refunded_val,
                    "remain",
                    remain,
                )
                break
    except YooKassaError as exc:
        print("LIST_PAYMENTS_ERR", getattr(exc, "code", ""), str(exc)[:200])

    # 2) If none — create payment with test bank_card (may still need confirmation)
    if not pid:
        amount = Decimal("10.00")
        idem_pay = f"block4-pay-{uuid.uuid4()}"
        body = {
            "amount": {"value": "10.00", "currency": "RUB"},
            "capture": True,
            "description": "Ringoo Block4 TEST refund drill",
            "metadata": {"purpose": "block4_refund_drill"},
            "confirmation": {
                "type": "redirect",
                "return_url": str(
                    getattr(settings, "YOOKASSA_RETURN_URL", "") or "https://example.com/return"
                ),
            },
            # YooKassa test card path still typically needs user confirmation page
            "payment_method_data": {"type": "bank_card"},
        }
        try:
            payment = client._request(
                "POST", "/payments", body=body, idempotence_key=idem_pay
            )
        except YooKassaError as exc:
            print("CREATE_PAYMENT_ERR", getattr(exc, "code", ""), str(exc)[:300])
            print("BLOCKED: cannot create/find succeeded test payment for refund")
            return 12
        pid = str(payment.get("id") or "")
        status = str(payment.get("status") or "")
        paid = bool(payment.get("paid"))
        print("PAYMENT_ID", pid)
        print("PAYMENT_STATUS", status, "paid=", paid)
        conf = payment.get("confirmation") or {}
        if conf.get("confirmation_url"):
            print("CONFIRMATION_URL_PRESENT", True)
        for _ in range(8):
            if status == "succeeded":
                break
            time.sleep(1)
            payment = client.get_payment(pid)
            status = str(payment.get("status") or "")
            paid = bool(payment.get("paid"))
            print("POLL", status, "paid=", paid)
        if status != "succeeded":
            print(
                "BLOCKED: payment requires manual test-card confirmation in browser; "
                "API auth/test_mode verified, refund API not executed on succeeded payment"
            )
            return 13

    payment = client.get_payment(pid)
    amount_val = Decimal(str((payment.get("amount") or {}).get("value") or "0"))
    refunded_val = Decimal(str((payment.get("refunded_amount") or {}).get("value") or "0"))
    remain = amount_val - refunded_val
    print("PAYMENT_READY", pid, "remain", remain)
    if remain < Decimal("2.00"):
        print("BLOCKED: no refundable remainder on available payments")
        return 14

    part = min(Decimal("1.00"), (remain / Decimal("2")).quantize(Decimal("0.01")))
    if part < Decimal("0.01"):
        part = Decimal("0.01")
    rest = (remain - part).quantize(Decimal("0.01"))

    idem_r1 = f"block4-ref-partial-{pid}-{part}"
    r1 = client.create_refund(payment_id=pid, amount=part, idempotence_key=idem_r1)
    print(
        "REFUND1_ID",
        r1.get("id"),
        "status",
        r1.get("status"),
        "amount",
        (r1.get("amount") or {}).get("value"),
    )

    r1b = client.create_refund(payment_id=pid, amount=part, idempotence_key=idem_r1)
    print("REFUND1_REPLAY_SAME_ID", r1b.get("id") == r1.get("id"), "status", r1b.get("status"))

    if rest >= Decimal("0.01"):
        idem_r2 = f"block4-ref-rest-{pid}-{rest}"
        r2 = client.create_refund(payment_id=pid, amount=rest, idempotence_key=idem_r2)
        print(
            "REFUND2_ID",
            r2.get("id"),
            "status",
            r2.get("status"),
            "amount",
            (r2.get("amount") or {}).get("value"),
        )

    try:
        client.create_refund(
            payment_id=pid, amount=Decimal("0.01"), idempotence_key=f"block4-over-{pid}"
        )
        print("OVER_REFUND_UNEXPECTED_OK")
        return 16
    except YooKassaError as exc:
        print("OVER_REFUND_REJECTED", getattr(exc, "code", ""), str(exc)[:200])

    g1 = client.get_refund(str(r1.get("id")))
    print("GET_REFUND1", g1.get("status"), (g1.get("amount") or {}).get("value"))
    print("YK_REFUND_DRILL_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
