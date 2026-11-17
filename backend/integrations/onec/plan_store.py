"""
Хранение CatalogImportPlan в PostgreSQL + claim/APPLY (RELEASE 46.1 D.2.1/D.2.3).

Checksum: integrations.onec.plan_security.

D.2.3: право на execute — одноразовый execution_token в PostgreSQL.
Process-local PlanApplyCapability удалён (был подделываем).
"""

from __future__ import annotations

import secrets
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from integrations.onec.importer import (
    CatalogImportPlan,
    CategoryAction,
    ImportMode,
    ProductAction,
    SnapshotPolicy,
    StockAction,
    normalize_snapshot_policy,
)
from integrations.onec.plan_security import (
    CANONICAL_SCHEMA_VERSION,
    catalog_plan_checksum,
)

STORAGE_VERSION = 1
PLAN_TTL_MINUTES = 60

# Gates registered only after successful DB token consume (one-shot).
_LIVE_GATE_IDS: set[int] = set()


class PlanStoreError(ValueError):
    """Ошибка сериализации, хранения или проверки плана."""


class _ExecutionGate:
    """
    Одноразовый пропуск к _apply_catalog_import_plan.
    Создаётся только после успешного consume execution_token в PostgreSQL.
    Публичный конструктор без регистрации в _LIVE_GATE_IDS не проходит проверку.
    """

    __slots__ = ("plan_id",)

    def __init__(self, plan_id: uuid.UUID):
        self.plan_id = plan_id


def validate_and_consume_execution_gate(
    gate: Any, *, expected_plan_id: uuid.UUID
) -> None:
    """Вызывается executor'ом до первой записи каталога."""
    if not isinstance(gate, _ExecutionGate):
        raise PlanStoreError("APPLY requires execution gate from plan_store")
    if id(gate) not in _LIVE_GATE_IDS:
        raise PlanStoreError("Invalid or forged execution gate")
    if gate.plan_id != expected_plan_id:
        raise PlanStoreError("Execution gate plan_id mismatch")
    _LIVE_GATE_IDS.discard(id(gate))

def _req_str(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise PlanStoreError(f"{field} must be str, got {type(value).__name__}")
    return value


def _opt_str(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise PlanStoreError(f"{field} must be str|None, got {type(value).__name__}")


def _req_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PlanStoreError(f"{field} must be int, got {type(value).__name__}")
    return value


def _json_safe_scalar(value: Any, field: str) -> Any:
    """Скаляры для JSON payload без float/repr/default=str."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, Decimal):
        # Храним как строку фиксированной записи; при restore остаётся str в plan fields.
        text = format(value, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        if text in ("", "-0", "+0", "-"):
            return "0"
        return text.lstrip("+")
    raise PlanStoreError(f"{field}: unsupported type {type(value).__name__}")


def _json_safe_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PlanStoreError(f"{field} must be dict, got {type(value).__name__}")
    out: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise PlanStoreError(f"{field}: non-string key {type(key).__name__}")
        out[key] = _json_safe_value(item, f"{field}.{key}")
    return out


def _json_safe_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, (list, tuple)):
        raise PlanStoreError(f"{field} must be list, got {type(value).__name__}")
    return [_json_safe_value(item, f"{field}[]") for item in value]


def _json_safe_value(value: Any, field: str) -> Any:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return _json_safe_scalar(value, field)
    if isinstance(value, dict):
        return _json_safe_mapping(value, field)
    if isinstance(value, (list, tuple)):
        return _json_safe_list(value, field)
    raise PlanStoreError(f"{field}: unsupported type {type(value).__name__}")


def _ser_category(action: CategoryAction) -> dict[str, Any]:
    if not isinstance(action, CategoryAction):
        raise PlanStoreError("categories[] must be CategoryAction")
    return {
        "onec_code": _req_str(action.onec_code, "category.onec_code"),
        "name": _req_str(action.name, "category.name"),
        "parent_code": _req_str(action.parent_code, "category.parent_code"),
        "action": _req_str(action.action, "category.action"),
        "site_id": _opt_str(action.site_id, "category.site_id"),
        "site_slug": _opt_str(action.site_slug, "category.site_slug"),
        "notes": _req_str(action.notes, "category.notes"),
    }


def _ser_product(action: ProductAction) -> dict[str, Any]:
    if not isinstance(action, ProductAction):
        raise PlanStoreError("products[] must be ProductAction")
    return {
        "onec_code": _req_str(action.onec_code, "product.onec_code"),
        "name": _req_str(action.name, "product.name"),
        "parent_code": _req_str(action.parent_code, "product.parent_code"),
        "price": _opt_str(action.price, "product.price"),
        "action": _req_str(action.action, "product.action"),
        "site_id": _opt_str(action.site_id, "product.site_id"),
        "site_slug": _opt_str(action.site_slug, "product.site_slug"),
        "matched_by": _req_str(action.matched_by, "product.matched_by"),
        "notes": _req_str(action.notes, "product.notes"),
    }


def _ser_stock(action: StockAction) -> dict[str, Any]:
    if not isinstance(action, StockAction):
        raise PlanStoreError("stocks[] must be StockAction")
    return {
        "onec_code": _req_str(action.onec_code, "stock.onec_code"),
        "sklad": _req_str(action.sklad, "stock.sklad"),
        "sklad_id": _req_str(action.sklad_id, "stock.sklad_id"),
        "quantity": _opt_str(action.quantity, "stock.quantity"),
        "quantity_status": _req_str(action.quantity_status, "stock.quantity_status"),
        "action": _req_str(action.action, "stock.action"),
        "notes": _req_str(action.notes, "stock.notes"),
        "series": _req_str(action.series, "stock.series"),
        "series_id": _req_str(action.series_id, "stock.series_id"),
        "site_product_id": _opt_str(action.site_product_id, "stock.site_product_id"),
        "site_store_id": _opt_str(action.site_store_id, "stock.site_store_id"),
    }


def serialize_catalog_plan(plan: CatalogImportPlan) -> dict[str, Any]:
    """Полный JSON-совместимый payload для восстановления плана."""
    if not isinstance(plan, CatalogImportPlan):
        raise PlanStoreError(
            f"Expected CatalogImportPlan, got {type(plan).__name__}"
        )
    return {
        "storage_version": STORAGE_VERSION,
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "mode": _req_str(plan.mode, "mode"),
        "generated_at": _req_str(plan.generated_at, "generated_at"),
        "source_folders_path": _req_str(
            plan.source_folders_path, "source_folders_path"
        ),
        "source_products_path": _req_str(
            plan.source_products_path, "source_products_path"
        ),
        "run_id": _req_str(plan.run_id, "run_id"),
        "snapshot_policy": _req_str(plan.snapshot_policy, "snapshot_policy"),
        "folder_count": _req_int(plan.folder_count, "folder_count"),
        "product_row_count": _req_int(plan.product_row_count, "product_row_count"),
        "unique_product_count": _req_int(
            plan.unique_product_count, "unique_product_count"
        ),
        "categories": [_ser_category(c) for c in plan.categories],
        "products": [_ser_product(p) for p in plan.products],
        "stocks": [_ser_stock(s) for s in plan.stocks],
        "stocks_to_zero": [_ser_stock(s) for s in plan.stocks_to_zero],
        "warehouses": [
            _json_safe_mapping(w, "warehouses[]") for w in plan.warehouses
        ],
        "issues": [_json_safe_mapping(i, "issues[]") for i in plan.issues],
        "apply_blockers": [
            _json_safe_mapping(b, "apply_blockers[]") for b in plan.apply_blockers
        ],
        "summary": _json_safe_mapping(plan.summary, "summary"),
    }


def _de_category(data: Any) -> CategoryAction:
    if not isinstance(data, dict):
        raise PlanStoreError("category must be dict")
    return CategoryAction(
        onec_code=_req_str(data.get("onec_code"), "category.onec_code"),
        name=_req_str(data.get("name"), "category.name"),
        parent_code=_req_str(data.get("parent_code"), "category.parent_code"),
        action=_req_str(data.get("action"), "category.action"),
        site_id=_opt_str(data.get("site_id"), "category.site_id"),
        site_slug=_opt_str(data.get("site_slug"), "category.site_slug"),
        notes=_req_str(data.get("notes", ""), "category.notes"),
    )


def _de_product(data: Any) -> ProductAction:
    if not isinstance(data, dict):
        raise PlanStoreError("product must be dict")
    return ProductAction(
        onec_code=_req_str(data.get("onec_code"), "product.onec_code"),
        name=_req_str(data.get("name"), "product.name"),
        parent_code=_req_str(data.get("parent_code"), "product.parent_code"),
        price=_opt_str(data.get("price"), "product.price"),
        action=_req_str(data.get("action"), "product.action"),
        site_id=_opt_str(data.get("site_id"), "product.site_id"),
        site_slug=_opt_str(data.get("site_slug"), "product.site_slug"),
        matched_by=_req_str(data.get("matched_by", ""), "product.matched_by"),
        notes=_req_str(data.get("notes", ""), "product.notes"),
    )


def _de_stock(data: Any) -> StockAction:
    if not isinstance(data, dict):
        raise PlanStoreError("stock must be dict")
    return StockAction(
        onec_code=_req_str(data.get("onec_code"), "stock.onec_code"),
        sklad=_req_str(data.get("sklad"), "stock.sklad"),
        sklad_id=_req_str(data.get("sklad_id"), "stock.sklad_id"),
        quantity=_opt_str(data.get("quantity"), "stock.quantity"),
        quantity_status=_req_str(
            data.get("quantity_status"), "stock.quantity_status"
        ),
        action=_req_str(data.get("action"), "stock.action"),
        notes=_req_str(data.get("notes", ""), "stock.notes"),
        series=_req_str(data.get("series", ""), "stock.series"),
        series_id=_req_str(data.get("series_id", ""), "stock.series_id"),
        site_product_id=_opt_str(
            data.get("site_product_id"), "stock.site_product_id"
        ),
        site_store_id=_opt_str(data.get("site_store_id"), "stock.site_store_id"),
    )


def deserialize_catalog_plan(
    payload: dict[str, Any],
    *,
    storage_version: int | None = None,
) -> CatalogImportPlan:
    if not isinstance(payload, dict):
        raise PlanStoreError("payload must be dict")
    sv = storage_version if storage_version is not None else payload.get("storage_version")
    if sv != STORAGE_VERSION:
        raise PlanStoreError(f"Unsupported storage_version={sv!r}")
    schema = payload.get("schema_version")
    if schema != CANONICAL_SCHEMA_VERSION:
        raise PlanStoreError(f"Unsupported schema_version={schema!r}")

    cats = payload.get("categories")
    prods = payload.get("products")
    stocks = payload.get("stocks")
    zeros = payload.get("stocks_to_zero")
    if not isinstance(cats, list) or not isinstance(prods, list):
        raise PlanStoreError("categories/products must be lists")
    if not isinstance(stocks, list) or not isinstance(zeros, list):
        raise PlanStoreError("stocks/stocks_to_zero must be lists")
    warehouses = payload.get("warehouses")
    issues = payload.get("issues")
    blockers = payload.get("apply_blockers")
    summary = payload.get("summary")
    if not isinstance(warehouses, list) or not isinstance(issues, list):
        raise PlanStoreError("warehouses/issues must be lists")
    if not isinstance(blockers, list) or not isinstance(summary, dict):
        raise PlanStoreError("apply_blockers must be list; summary must be dict")

    return CatalogImportPlan(
        mode=_req_str(payload.get("mode"), "mode"),
        generated_at=_req_str(payload.get("generated_at"), "generated_at"),
        source_folders_path=_req_str(
            payload.get("source_folders_path"), "source_folders_path"
        ),
        source_products_path=_req_str(
            payload.get("source_products_path"), "source_products_path"
        ),
        run_id=_req_str(payload.get("run_id", ""), "run_id"),
        snapshot_policy=_req_str(payload.get("snapshot_policy"), "snapshot_policy"),
        folder_count=_req_int(payload.get("folder_count", 0), "folder_count"),
        product_row_count=_req_int(
            payload.get("product_row_count", 0), "product_row_count"
        ),
        unique_product_count=_req_int(
            payload.get("unique_product_count", 0), "unique_product_count"
        ),
        categories=[_de_category(c) for c in cats],
        products=[_de_product(p) for p in prods],
        stocks=[_de_stock(s) for s in stocks],
        stocks_to_zero=[_de_stock(s) for s in zeros],
        warehouses=[_json_safe_mapping(w, "warehouses[]") for w in warehouses],
        issues=[_json_safe_mapping(i, "issues[]") for i in issues],
        apply_blockers=[_json_safe_mapping(b, "apply_blockers[]") for b in blockers],
        summary=_json_safe_mapping(summary, "summary"),
    )


def persist_plan_after_dry_run(
    plan: CatalogImportPlan,
    *,
    user=None,
    dry_run_sync_log=None,
) -> Any:
    """
    Сохранить план после DRY-RUN со status=ready.
    Round-trip serialize→deserialize→checksum до записи.
    """
    from apps.products.sync_models import OneCCatalogImportPlan

    payload = serialize_catalog_plan(plan)
    checksum = catalog_plan_checksum(plan)
    restored = deserialize_catalog_plan(payload, storage_version=STORAGE_VERSION)
    restored_checksum = catalog_plan_checksum(restored)
    if restored_checksum != checksum:
        raise PlanStoreError(
            "Round-trip checksum mismatch — plan not saved as ready"
        )

    now = timezone.now()
    created_by = user if getattr(user, "is_authenticated", False) else None
    row = OneCCatalogImportPlan.objects.create(
        checksum=checksum,
        schema_version=CANONICAL_SCHEMA_VERSION,
        storage_version=STORAGE_VERSION,
        canonical_payload=payload,
        snapshot_policy=normalize_snapshot_policy(plan.snapshot_policy),
        status=OneCCatalogImportPlan.STATUS_READY,
        expires_at=now + timedelta(minutes=PLAN_TTL_MINUTES),
        created_by=created_by,
        dry_run_sync_log=dry_run_sync_log,
    )
    return row


def _parse_plan_id(plan_id: Any) -> uuid.UUID:
    if isinstance(plan_id, uuid.UUID):
        return plan_id
    if isinstance(plan_id, str):
        try:
            return uuid.UUID(plan_id)
        except (ValueError, TypeError) as exc:
            raise PlanStoreError(f"Invalid plan_id: {plan_id!r}") from exc
    raise PlanStoreError(f"Invalid plan_id type: {type(plan_id).__name__}")


def mark_plan_applied(row) -> None:
    from apps.products.sync_models import OneCCatalogImportPlan

    row.status = OneCCatalogImportPlan.STATUS_APPLIED
    row.applied_at = timezone.now()
    row.execution_token = ""
    row.save(update_fields=["status", "applied_at", "execution_token"])


def mark_plan_rejected(row, detail: str) -> None:
    from apps.products.sync_models import OneCCatalogImportPlan

    row.status = OneCCatalogImportPlan.STATUS_REJECTED
    row.error_detail = (detail or "")[:2000]
    row.execution_token = ""
    row.save(update_fields=["status", "error_detail", "execution_token"])


def _claim_plan_for_apply(
    plan_id: Any,
    *,
    full_snapshot_acknowledged: bool = False,
) -> tuple[CatalogImportPlan, Any, str]:
    """
    Атомарно: ready → applying + execution_token в PostgreSQL.
    full_snapshot требует full_snapshot_acknowledged=True (не наследуется от dry-run).
    При ошибке ack/валидации до перехода — статус ready сохраняется (кроме expire/reject payload).
    """
    from apps.products.sync_models import OneCCatalogImportPlan

    pid = _parse_plan_id(plan_id)
    failure: str | None = None
    success: tuple[CatalogImportPlan, Any, str] | None = None

    with transaction.atomic():
        try:
            row = (
                OneCCatalogImportPlan.objects.select_for_update()
                .get(pk=pid)
            )
        except OneCCatalogImportPlan.DoesNotExist as exc:
            raise PlanStoreError(f"Plan not found: {pid}") from exc

        if (
            row.status == OneCCatalogImportPlan.STATUS_READY
            and row.expires_at <= timezone.now()
        ):
            row.status = OneCCatalogImportPlan.STATUS_EXPIRED
            row.error_detail = "TTL expired"
            row.save(update_fields=["status", "error_detail"])
            failure = "Plan expired"
        elif row.status != OneCCatalogImportPlan.STATUS_READY:
            failure = f"Plan status={row.status!r} is not ready for APPLY"
        elif row.schema_version != CANONICAL_SCHEMA_VERSION:
            mark_plan_rejected(
                row, f"schema_version mismatch: {row.schema_version}"
            )
            failure = "Unsupported schema_version on stored plan"
        elif row.storage_version != STORAGE_VERSION:
            mark_plan_rejected(
                row, f"storage_version mismatch: {row.storage_version}"
            )
            failure = "Unsupported storage_version on stored plan"
        else:
            try:
                plan = deserialize_catalog_plan(
                    row.canonical_payload, storage_version=row.storage_version
                )
            except PlanStoreError as exc:
                mark_plan_rejected(row, str(exc))
                failure = str(exc)
            else:
                recomputed = catalog_plan_checksum(plan)
                if not isinstance(row.checksum, str) or len(row.checksum) != 64:
                    mark_plan_rejected(row, "invalid checksum field")
                    failure = "Invalid stored checksum"
                elif recomputed != row.checksum:
                    mark_plan_rejected(row, "checksum mismatch on restore")
                    failure = "Stored plan checksum mismatch"
                elif plan.apply_blockers:
                    mark_plan_rejected(row, "apply_blockers present")
                    failure = "Plan has apply_blockers"
                else:
                    policy = normalize_snapshot_policy(plan.snapshot_policy)
                    if policy != row.snapshot_policy:
                        mark_plan_rejected(
                            row, "snapshot_policy row/payload mismatch"
                        )
                        failure = "snapshot_policy mismatch"
                    elif (
                        policy == SnapshotPolicy.PRESENT_ONLY.value
                        and plan.stocks_to_zero
                    ):
                        mark_plan_rejected(
                            row,
                            "present_only plan must not contain stocks_to_zero",
                        )
                        failure = (
                            "present_only plan must not contain stocks_to_zero"
                        )
                    elif (
                        policy == SnapshotPolicy.FULL_SNAPSHOT.value
                        and not full_snapshot_acknowledged
                    ):
                        # Stay ready — caller can retry with ack.
                        failure = (
                            "full_snapshot APPLY requires "
                            "full_snapshot_acknowledged=True"
                        )
                    else:
                        token = secrets.token_hex(32)
                        plan.mode = ImportMode.APPLY.value
                        now = timezone.now()
                        row.status = OneCCatalogImportPlan.STATUS_APPLYING
                        row.applying_at = now
                        row.execution_token = token
                        row.save(
                            update_fields=[
                                "status",
                                "applying_at",
                                "execution_token",
                            ]
                        )
                        success = (plan, row, token)

    if failure:
        raise PlanStoreError(failure)
    if success is None:
        raise PlanStoreError("Claim failed without detail")
    return success


def _consume_execution_token(
    plan_id: uuid.UUID, token: str
) -> _ExecutionGate:
    """Сверяет и обнуляет execution_token в PostgreSQL; выдаёт one-shot gate."""
    from apps.products.sync_models import OneCCatalogImportPlan

    if not token or not isinstance(token, str):
        raise PlanStoreError("Missing execution token")
    with transaction.atomic():
        try:
            row = (
                OneCCatalogImportPlan.objects.select_for_update()
                .get(pk=plan_id)
            )
        except OneCCatalogImportPlan.DoesNotExist as exc:
            raise PlanStoreError(f"Plan not found: {plan_id}") from exc
        if row.status != OneCCatalogImportPlan.STATUS_APPLYING:
            raise PlanStoreError(
                f"Cannot consume token: status={row.status!r}"
            )
        if not row.execution_token or row.execution_token != token:
            raise PlanStoreError("Invalid or already consumed execution token")
        row.execution_token = ""
        row.save(update_fields=["execution_token"])
        gate = _ExecutionGate(plan_id)
        _LIVE_GATE_IDS.add(id(gate))
        return gate


def apply_saved_plan(
    plan_id: Any,
    *,
    full_snapshot_acknowledged: bool = False,
) -> dict[str, Any]:
    """
    Единственная публичная точка APPLY сохранённого плана.
    claim (DB) → consume token (DB) → catalog apply → applied/rejected.
    """
    from integrations.onec.importer import _apply_catalog_import_plan

    plan, row, token = _claim_plan_for_apply(
        plan_id, full_snapshot_acknowledged=full_snapshot_acknowledged
    )
    try:
        gate = _consume_execution_token(row.plan_id, token)
        result = _apply_catalog_import_plan(
            plan, gate=gate, expected_plan_id=row.plan_id
        )
        # refresh row after consume
        row.refresh_from_db()
        mark_plan_applied(row)
        return result
    except Exception as exc:
        row.refresh_from_db()
        if row.status == type(row).STATUS_APPLYING:
            mark_plan_rejected(row, str(exc)[:2000])
        raise


def apply_catalog_import_by_plan_id(
    plan_id: Any,
    *,
    full_snapshot_acknowledged: bool = False,
) -> dict[str, Any]:
    """Alias для совместимости вызовов catalog_sync / importer."""
    return apply_saved_plan(
        plan_id, full_snapshot_acknowledged=full_snapshot_acknowledged
    )


def diagnose_stuck_applying_plan(plan_id: Any) -> dict[str, Any]:
    """
    Диагностика зависшего applying — без смены статуса.

    Ручная процедура (ops):
    1) Вызвать diagnose_stuck_applying_plan(plan_id) — зафиксировать applying_at,
       execution_token_present, SyncLog, error_detail.
    2) Проверить в PostgreSQL/каталоге, закоммитились ли изменения (сверка с
       dry-run plan payload / SyncLog). Не полагаться только на TTL.
    3) Если доказан полный rollback / запись не выполнялась →
       manually_resolve_stuck_plan(..., resolution='rejected', note=...).
    4) Если доказано успешное применение каталога →
       resolution='applied_confirmed' + note с доказательством.
    5) Запрещено: applying → ready; повторный APPLY при неопределённости;
       авто-resolve по TTL.
    """
    from apps.products.sync_models import OneCCatalogImportPlan

    pid = _parse_plan_id(plan_id)
    try:
        row = OneCCatalogImportPlan.objects.select_related(
            "dry_run_sync_log", "created_by", "resolved_by"
        ).get(pk=pid)
    except OneCCatalogImportPlan.DoesNotExist as exc:
        raise PlanStoreError(f"Plan not found: {pid}") from exc

    sync = row.dry_run_sync_log
    return {
        "plan_id": str(row.plan_id),
        "status": row.status,
        "snapshot_policy": row.snapshot_policy,
        "checksum": row.checksum,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "applying_at": row.applying_at.isoformat() if row.applying_at else None,
        "applied_at": row.applied_at.isoformat() if row.applied_at else None,
        "execution_token_present": bool(row.execution_token),
        "error_detail": row.error_detail or "",
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "resolution_note": row.resolution_note or "",
        "resolved_by_id": str(row.resolved_by_id) if row.resolved_by_id else None,
        "dry_run_sync_log_id": str(sync.pk) if sync else None,
        "dry_run_sync_log_run_id": sync.run_id if sync else None,
        "dry_run_sync_log_status": sync.status if sync else None,
        "note": (
            "Stuck applying: do not return to ready without proving full rollback. "
            "Use manually_resolve_stuck_plan with audit note."
        ),
    }


def manually_resolve_stuck_plan(
    plan_id: Any,
    *,
    resolution: str,
    note: str,
    user=None,
) -> dict[str, Any]:
    """
    Ручное разрешение applying без возврата в ready.
    resolution: rejected | applied_confirmed
    """
    from apps.products.sync_models import OneCCatalogImportPlan

    if resolution not in (
        OneCCatalogImportPlan.STATUS_REJECTED,
        "applied_confirmed",
    ):
        raise PlanStoreError(
            "resolution must be 'rejected' or 'applied_confirmed'"
        )
    if not (note or "").strip():
        raise PlanStoreError("resolution note is required for audit trail")

    pid = _parse_plan_id(plan_id)
    with transaction.atomic():
        row = OneCCatalogImportPlan.objects.select_for_update().get(pk=pid)
        if row.status != OneCCatalogImportPlan.STATUS_APPLYING:
            raise PlanStoreError(
                f"manual resolve only for applying, got {row.status!r}"
            )
        now = timezone.now()
        row.resolved_at = now
        row.resolution_note = note.strip()[:2000]
        row.resolved_by = user if getattr(user, "is_authenticated", False) else None
        row.execution_token = ""
        if resolution == "applied_confirmed":
            row.status = OneCCatalogImportPlan.STATUS_APPLIED
            row.applied_at = now
            row.error_detail = (
                f"manual resolve applied_confirmed: {note.strip()[:500]}"
            )
        else:
            row.status = OneCCatalogImportPlan.STATUS_REJECTED
            row.error_detail = (
                f"manual resolve rejected: {note.strip()[:500]}"
            )
        row.save(
            update_fields=[
                "status",
                "applied_at",
                "error_detail",
                "execution_token",
                "resolved_at",
                "resolution_note",
                "resolved_by",
            ]
        )
    return diagnose_stuck_applying_plan(pid)
