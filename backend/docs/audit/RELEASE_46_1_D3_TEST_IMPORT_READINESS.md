# RELEASE 46.1 — Stage D.3 Test Import Contour Readiness

**Mode:** READ-ONLY  
**Date:** 2026-11-17  
**No APPLY / migrate / 1С GET / payments / Docker change / git write / leftover edits**

---

## 1. Тестовая БД

| Вопрос | Факт |
|--------|------|
| Unit-test settings | `config.settings.test` |
| Unit-test DB | SQLite `:memory:` |
| Migrations in unit tests | `MIGRATION_MODULES = DisableMigrations()` — таблицы из моделей, не через migrate |
| Local `manage.py` default | `config.settings.development` loads `.env.development` **before** `.env` |
| Current development DB | PostgreSQL `NAME=ringoo`, `HOST=db`, `PORT=5432` (Docker Compose service) |
| Local reachability now | **Unreachable** (`getaddrinfo failed` for host `db`; Docker Desktop недоступен в этой сессии) |
| Production settings | Separate `config.settings.production` + `.env.production` (not loaded by development) |
| Isolation proof | **Not proven** for import drills: `ringoo@db` is the **main local compose DB**, not a dedicated `ringoo_test` / import sandbox |
| `config.settings.test_postgres` | Exists for concurrency; requires `DATABASE_URL` → named test DB + real migrations |

### Миграции каталога / складов / планов

| App | Relevant migrations |
|-----|---------------------|
| products | `0006` onec codes … `0008` SyncLog … **`0010_onec_catalog_import_plan`** → **`0011_onec_plan_execution_token`** |
| stores | through `0009` (series, confirmed warehouses, stock protect) |

**0010 → 0011:** `0011.dependencies = [("products", "0010_onec_catalog_import_plan")]`.

**Applied in local contour:** **NOT VERIFIED** (cannot connect to `db`). Migrations **not** applied in this stage (forbidden).

### Safety

Cannot prove a safe, isolated, migrated test DB for D.4/D.5 right now → **STOP on DB readiness** until an explicit import-test database is designated and reachable.

---

## 2. GET-контур 1С (код, без запросов)

| Item | Fact |
|------|------|
| Endpoints | `CatalogFolders/folders`, `CatalogProducts/products` (`OneCEndpoints`) |
| Methods for catalog | **GET only** via `fetch_folders_xml` / `fetch_products_xml` |
| Write methods exist | `register_partner`, order POST/cancel — **not** used by catalog import path |
| Auth | Basic Auth headers if login set; values **not** present in any local `.env*` (`ONE_C_*` keys: **NONE**) |
| Timeout | `ONE_C_API_TIMEOUT` default **60** |
| Max body | 20 MiB |
| Empty XML | `OneCClientError` («Пустой XML…») |
| HTTP errors | Mapped public messages; raises `OneCClientError` |
| `/ut11_test/hs/` | **Hard-blocked** in `normalize_onec_base_url` |
| `/razrab/hs` | Required suffix; `http://192.168.10.2:1080/razrab/hs` normalizes OK |
| Current settings | `ONE_C_API_ENABLED=False`, base `http://localhost/razrab/hs`, credentials empty |

Live GET on this stage: **not performed** (per brief). Contour **not configured** for the expected test host yet.

---

## 3. Импорт каталога (фактический путь)

```
GET/XML → parse folders/products → plan_from_parsed → CatalogImportPlan
  → (dry-run) persist_plan_after_dry_run → OneCCatalogImportPlan(ready)
  → (later APPLY) apply_saved_plan(plan_id, full_snapshot_acknowledged=…)
```

Checked behaviors (code, no rewrite):

| Concern | Behavior |
|---------|----------|
| Series | Stock identity `(product, store, onec_series_id)`; series rows planned separately |
| Same product / different warehouses | Separate stock rows by `sklad_id` |
| `warehouseId` | Required; missing/unknown → skip + issues/blockers; Store not auto-created |
| Missing category | Product skip + issues; narrow stock skip path for missing category |
| Empty price/qty | `writable_price` / `writable_quantity` → `None` (not coerced to 0) |
| `present_only` zeros | `stocks_to_zero` only if `full_snapshot`; apply defense rejects zeros under present_only |
| Reserved | Stock upsert does **not** overwrite `reserved_quantity` (`stock_ops`) |
| Re-import duplicates | Products keyed by `onec_code`; stock unique `(product, store, onec_series_id)`; idempotent skip in batch upsert |

---

## 4. DRY-RUN plan storage

| Item | Fact |
|------|------|
| Persist | `persist_plan_after_dry_run`: serialize + round-trip checksum + row `ready` |
| TTL | `PLAN_TTL_MINUTES = 60` |
| Restore | `deserialize_catalog_plan` + checksum recompute on claim |
| Policy | Stored `snapshot_policy`; mismatch → reject |
| Expired | `ready` + past `expires_at` → `expired` on claim |
| XML change after dry-run | Irrelevant to APPLY: APPLY uses **stored** payload only (no re-fetch) |
| APPLY without re-read 1С | **Yes** — `apply_saved_plan(plan_id)` / `apply_catalog_import_by_plan_id` |

---

## 5. XML выгрузки 17.11.2026

**Not found** in `C:\ringoo`, Desktop, Downloads, Documents (no matching 1С XML dated 2026-11-17).

Available only:
- `integrations/onec/fixtures/sample_*.xml` (tiny samples, Oct 2026)
- synthetic `backend/var/b8_018_fixtures/*` (load-test, Nov 14)

Cannot report category/product counts for the 17.11 dump (absent). SKU `00-00030516` — **not checked** (no file).

---

## 6. Risks / blockers (before D.4)

1. **No isolated migrated DB** proven reachable for import drills.  
2. **ONE_C credentials / ENABLED / base URL** not set for `192.168.10.2:1080/razrab/hs`.  
3. **Confirmed warehouse Store mapping** must exist in the chosen test DB or dry-run will block APPLY.  
4. PostgreSQL concurrent claim still **NOT VERIFIED** (D.2.4 condition; required before **production** APPLY, not blocking dry-run).  
5. Development DB name `ringoo` on compose is **not** a disposable import sandbox — do not APPLY there without explicit ACK.

---

## 7. Exact commands for D.4 (after unblock)

**Unblock checklist (config only; not done here):**
1. Create/select isolated DB e.g. `ringoo_import_test` (not production, not shared prod volume).  
2. Point a **non-production** settings/env at that DB; apply migrations including `0010`+`0011` **on that DB only** (separate stage).  
3. Set `ONE_C_API_BASE_URL=http://192.168.10.2:1080/razrab/hs`, credentials, `ONE_C_API_ENABLED=true` in that env.  
4. Ensure confirmed warehouses mapped (`list_onec_warehouses` / Store rows).  
5. Save GET XML to disk for audit trail.

**D.4 commands (Windows / PowerShell sketch):**

```bat
cd backend
set DJANGO_SETTINGS_MODULE=config.settings.development
REM ensure env targets ringoo_import_test + ONE_C_* as above

python manage.py import_onec_catalog --from-api --report var\d4_dryrun_report.json
```

Optional: also persist raw XML via a thin wrapper later; today CLI dry-run does not write XML files by default — capture with a separate approved GET dump script in D.4 if required.

**PASS D.4:**
- status success/partial (no stop blocker unexpected)
- `plan_id`, `plan_checksum`, `plan_expires_at` in report
- SyncLog dry_run=true
- snapshot_policy as intended (default present_only)
- blockers listed; APPLY not run

**FAIL D.4:** HTTP/auth/XML errors; empty bodies; cannot persist plan; wrong base URL / ut11; writes to wrong DB.

**Data touched in D.4:** SyncLog + `OneCCatalogImportPlan` rows only (no Product/Stock APPLY).

---

## 8. Plan D.5–D.7

### D.5 — Test APPLY
- **Where:** same isolated test DB only  
- **Cmd:**
```bat
python manage.py import_onec_catalog --apply --plan-id <UUID> --i-understand-apply --report var\d5_apply_report.json
```
  For full_snapshot plans add `--full-snapshot --i-understand-full-snapshot`.  
  Or: `apply_saved_plan(plan_id, full_snapshot_acknowledged=…)` in a controlled shell on test settings.  
- ** Preconditions:** backup or recreate DB; migrations applied; dry-run blockers empty/acceptable; TTL valid; correct policy ack  
- **Touches:** Category/Product/Stock (+ movements) per plan  
- **PASS:** plan status `applied`; counters match dry-run intent; no unexpected zeros under present_only  
- **FAIL:** claim/ack errors; blockers; wrong DB; catalog partial without reject

### D.6 — Post-APPLY verification
- Compare DB vs dry-run report / saved XML: category codes, product `onec_code`, prices, warehouses, series stock rows, quantities, reserved unchanged where not in plan  
- Spot-check SKU of interest (e.g. `00-00030516` if present in dump)  
- **PASS:** match within documented skips/blockers  
- **FAIL:** missing/extra rows, price/qty coercion, reserved clobber, series merged

### D.7 — Idempotency
- Second `--from-api` dry-run → new `plan_id`  
- APPLY again (or compare plan: mostly updates/skips)  
- **PASS:** no duplicate products/stocks; idempotent skips; reserved stable  
- **FAIL:** duplicate keys, quantity thrash, series loss

### Carry-forward condition
Run `RINGOO_TEST_POSTGRES=1` concurrent claim tests before any **production** APPLY enablement.

---

## 9. Verdict

### **BLOCKED** for immediate D.4 live GET + dry-run

**Why:** test DB isolation/migrations not proven; 1С GET contour not configured (enabled/creds/URL); no local 17.11 XML fallback.

**Code readiness:** parser, importer, plan_store, CLI dry-run→plan_id path are **ready** once contour unblocked.

**Next action (D.4 entry):** configure isolated DB + ONE_C test env (and warehouse map), then run the D.4 command block above — no need to re-audit D.1–D.2.4 unless a new defect appears.
