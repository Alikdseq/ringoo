# RELEASE 46.1 — D.2.4 Finalization Report

**Mode:** restore HOLD leftover (ACK) + READ-ONLY security audit  
**Date:** 2026-11-17  
**Git write / migrate / production APPLY / 1С write / payments / Docker/network:** not performed  
**D.3:** not started

---

## A. Restoration

| Item | Value |
|------|-------|
| File | `backend/scripts/b8_018_zero_smoke.py` |
| Action | Restored logical **v0** from Agent transcript Write #4089 |
| Includes | `apply_catalog_import(plan2)` inside `transaction.atomic()` |
| Compatibility with D.2 APPLY | **Not** attempted (HOLD artifact; will raise `PermissionError` if run) |
| Script executed | **No** |
| HOLD status | Preserved (`??` untracked; not CI) |
| SHA-256 (disk = LF) | `423C5CBAE2A8B51F0807F83AFC2520917598FAAFC8F7349AF01A6798B2D29A06` |
| LF match vs v0 | **True** |
| Original CRLF bytes | **Not confirmed** (restored LF as in transcript Write) |
| Other RELEASE 42 leftovers | **Not modified** |

Touched files this stage: **only** `backend/scripts/b8_018_zero_smoke.py` (+ this audit doc).

---

## B. Security audit table

| Проверка | Result | Evidence |
|---|---|---|
| Executor without DB claim | **PASS** | `validate_and_consume_execution_gate` requires live `_ExecutionGate`; forged/object gates fail before Category writes (`test_forged_*`, `test_executor_without_claim`, `test_reject_before_write`) |
| Token / gate reuse | **PASS** | `_consume_execution_token` clears DB token; gate id discarded from `_LIVE_GATE_IDS` (`test_token_reuse`, `test_gate_reuse`) |
| Gate other `plan_id` | **PASS** | `gate.plan_id != expected_plan_id` → `PlanStoreError` (`test_gate_other_plan_id`) |
| Gate checked before first catalog write | **PASS** | First statements of `_apply_catalog_import_plan` call `validate_and_consume_execution_gate` before category loop |
| Production path must use `apply_saved_plan` | **PASS** | `apply_catalog_import` → `PermissionError`; aliases delegate to `apply_saved_plan`; `catalog_sync` APPLY → `apply_saved_plan` |
| Other APPLY executors | **PASS** | Grep: only `apply_saved_plan` calls `_apply_catalog_import_plan` (tests are negative/security) |
| Claim atomicy (`ready→applying`+token) | **PASS** | `_claim_plan_for_apply` single `transaction.atomic` + `select_for_update` |
| Consume atomicy | **PASS** | Separate `atomic`+`select_for_update`; clears token |
| Claim+consume single atomic | **PASS WITH NOTE** | Two transactions by design; crash window → stuck `applying` (documented; no auto→ready) |
| `confirm=true` ≠ FS ack | **PASS** | Admin: separate `full_snapshot_acknowledged`; `test_admin_confirm_alone_not_full_snapshot_ack` |
| FS ack required on APPLY for `full_snapshot` | **PASS** | Claim lines 488–496; CLI `full_snapshot_acknowledged = apply and full_snapshot and ack_full`; Celery kwarg; tests CLI/Celery/claim |
| `present_only` without FS ack | **PASS** | Claim skips ack check; `test_present_only_without_fs_ack`, CLI present_only apply test |
| Bypass claim via internal API | **PASS** | Direct executor needs live gate from consume; public apply closed |
| Helper gated by `TESTING` | **PASS** | `tests/onec_plan_apply_helpers.py`; `TESTING=True` only in `config.settings.test`; production/dev have no `TESTING` → getattr False; `test_helper_blocked_outside_testing` |
| Helper not on production path | **PASS** | Only under `tests/` (+ no smoke import after restore) |
| No auto `applying→ready` | **PASS** | No code path sets ready from applying; manual resolve forbids ready |
| Manual resolve note + audit | **PASS** | note required; `resolved_at`/`resolution_note`/`resolved_by`/`error_detail` |
| Re-APPLY after indeterminate | **PASS** | status `applying`/`applied`/`rejected` refuses claim |
| `applied_confirmed` without proof | **PASS WITH NOTE** | Allowed by design (ops trust); can mark applied without catalog proof — residual process risk |
| Mid-apply rollback | **PASS** | `_apply_catalog_import_plan` `@transaction.atomic`; `test_rollback_catalog_on_apply_error` |
| Crash after catalog commit before `mark_plan_applied` | **PASS WITH NOTE** | Leaves `applying`; diagnose/manual resolve; no silent ready |
| PostgreSQL concurrent claim | **NOT VERIFIED** | Test exists; 2 skipped without `RINGOO_TEST_POSTGRES` |
| RELEASE 42 leftover integrity | **PASS** (after restore) | smoke restored to v0; other leftovers untouched |
| D.2.2 forgeable capability | **PASS** (fixed) | DB token + live gate |
| D.2.2 ungated helper | **PASS** (fixed) | test-only + TESTING |
| D.2.2 FS ack gaps | **PASS** (fixed) | CLI/Admin/Celery/claim |
| D.2.2 stuck auto-ready | **PASS** (fixed) | diagnose + manual only |

---

## C. Tests

Commands:

```text
set DJANGO_SETTINGS_MODULE=config.settings.test
python -m pytest tests/test_r46_plan_store.py -q --override-ini="addopts=" --tb=line
python -m pytest tests/test_r46_plan_store.py tests/test_r46_present_only_snapshot.py tests/test_r46_missing_category_stock_skip.py tests/test_r46_plan_checksum.py tests/test_block8_catalog_guards.py tests/test_onec_block7_reporting_guards.py tests/test_onec_stock_reconciliation.py tests/test_onec_stock_idempotency.py tests/test_onec_http.py tests/test_onec_block3_series_cart.py tests/test_onec_sync_log.py tests/test_onec_block4_orders_locks.py tests/test_r46_plan_store_concurrent_postgres.py -q --override-ini="addopts=" --tb=line
```

Results:

| Suite | Result |
|-------|--------|
| `test_r46_plan_store.py` | **42 passed** |
| D.2.1/D.2.3 regression set | **194 passed, 2 skipped** |
| Skipped | `test_r46_plan_store_concurrent_postgres.py` (no `RINGOO_TEST_POSTGRES`) |
| PostgreSQL concurrency | **NOT VERIFIED** (not counted as pass) |

---

## D. Final verdict

### **ACCEPTED WITH CONDITIONS**

D.2.3 security fixes are accepted for progression past D.2.4 audit, with conditions:

1. **Run** `tests/test_r46_plan_store_concurrent_postgres.py` on isolated test PostgreSQL before production APPLY enablement / D.3 go-live decisions.
2. **Ops:** `manually_resolve_stuck_plan(..., applied_confirmed)` remains a privileged trust action — document runbook; do not use without catalog proof.
3. **HOLD:** `b8_018_zero_smoke.py` restored to v0; intentionally incompatible with closed `apply_catalog_import`; do not run; do not “fix” without separate ACK.
4. Residual in-process risk: compromised worker code can still manipulate `_LIVE_GATE_IDS` after DB claim — accepted trust boundary.

### D.2.2 findings disposition

| Finding | Status |
|---------|--------|
| Forgeable PlanApplyCapability | Eliminated |
| Ungated `persist_and_apply_for_tests` in production module | Eliminated |
| FS ack missing on Admin/Celery APPLY | Eliminated |
| Stuck applying auto→ready | Eliminated (never implemented post-fix; diagnose/manual only) |

### Next stage (not started)

- Optional: D.2.4.1 / D.2.5 — PostgreSQL concurrent claim verification when test DB credentials available.
- Do **not** start D.3 until product owner confirms conditions above.
