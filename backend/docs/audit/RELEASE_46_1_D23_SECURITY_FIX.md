# RELEASE 46.1 — Stage D.2.3 Security Fix Report

Режим: локальная разработка / тестовая среда. Production APPLY, 1С write, платежи,
Docker/сеть, git commit/push — не выполнялись.

## 1. Изменённые файлы (D.2.3 focus)

| Файл | Изменение |
|------|-----------|
| `integrations/onec/plan_store.py` | DB `execution_token`, `_ExecutionGate`, `apply_saved_plan`, FS ack на claim, diagnose/manual resolve |
| `integrations/onec/importer.py` | `_apply_catalog_import_plan(gate=...)`; публичный `apply_catalog_import` закрыт |
| `integrations/onec/catalog_sync.py` | APPLY → `apply_saved_plan(..., full_snapshot_acknowledged=)` |
| `apps/products/sync_models.py` | `applying_at`, `execution_token`, `resolved_*` |
| `apps/products/migrations/0011_onec_plan_execution_token.py` | Локальная миграция модели |
| `apps/products/tasks.py` | `full_snapshot_acknowledged` |
| `apps/admin_api/views/onec_sync.py` | Отдельный `full_snapshot_acknowledged` ≠ `confirm` |
| `apps/products/management/commands/import_onec_catalog.py` | FS ack только из флагов сессии APPLY |
| `config/settings/test.py` | `TESTING = True` (Django 5 больше не выставляет) |
| `tests/onec_plan_apply_helpers.py` | **Новый** test-only helper |
| `tests/test_r46_plan_store.py` | Security / FS / stuck / rollback |
| `tests/test_r46_plan_store_concurrent_postgres.py` | **Новый** concurrent claim (PostgreSQL-only) |
| Тесты/smoke с helper | Импорты → `tests.onec_plan_apply_helpers` |

## 2. Новая архитектура capability

**Было (небезопасно):** публичный `PlanApplyCapability` + process-local `_CAPABILITY_NONCES`
— можно было сконструировать capability и вызвать executor без серверного claim.

**Стало:**

```
DRY-RUN → persist_plan_after_dry_run → status=ready + checksum
APPLY  → _claim_plan_for_apply(plan_id, full_snapshot_acknowledged)
           select_for_update: ready→applying, execution_token=secrets.token_hex(32)
       → _consume_execution_token(plan_id, token)
           select_for_update: token match → clear token; register _ExecutionGate in _LIVE_GATE_IDS
       → _apply_catalog_import_plan(plan, gate=gate, expected_plan_id=…)
           validate_and_consume_execution_gate (type + live id + plan_id) ДО первой записи
       → mark_plan_applied | mark_plan_rejected
```

Почему безопаснее:

1. Право на APPLY живёт в PostgreSQL (`execution_token`), не в mutable set nonce’ов.
2. Публичный конструктор `_ExecutionGate` без consume **не** проходит (`id(gate) not in _LIVE_GATE_IDS`).
3. Токен одноразовый и атомарно обнуляется в той же БД, что и статус.
4. Gate привязан к `plan_id`; чужой plan_id → отказ до записи.
5. Повтор consume / повтор gate → отказ.
6. Ошибка проверки gate → исключение до `Category.objects.create` / stocks.
7. HMAC не используется как единственная защита (секрет процесса недостаточен против in-process code).

Остаточный риск: код в том же процессе теоретически может дернуть `_consume_execution_token` / подставить id в `_LIVE_GATE_IDS` после DB claim — это уже компрометация trust boundary процесса, не HTTP/API.

## 3. Вызовы executor

| Место | Роль |
|-------|------|
| `plan_store.apply_saved_plan` | **Единственный** production путь к `_apply_catalog_import_plan` |
| `plan_store.apply_catalog_import_by_plan_id` | Alias → `apply_saved_plan` |
| `importer.apply_catalog_import_by_plan_id` | Alias → `apply_saved_plan` |
| `catalog_sync.run_catalog_import` (dry_run=False) | → `apply_saved_plan` |
| `importer.apply_catalog_import(...)` | `PermissionError` (закрыт) |
| Тесты | Прямой вызов `_apply_catalog_import_plan` только для negative security cases |

## 4. `persist_and_apply_for_tests`

| Место | Статус |
|-------|--------|
| `integrations/onec/plan_store.py` | **Удалён** |
| `tests/onec_plan_apply_helpers.py` | Единственная реализация; требует `settings.TESTING` |
| Тесты block3/7/8, stock_*, r46_*, http | Импорт из test helper |
| `scripts/b8_018_zero_smoke.py` | Импорт test helper; крутится под DiscoverRunner (`TESTING`) |

Вне `TESTING` → `RuntimeError`. Smoke не обходит APPLY без test DB runner.

## 5. full_snapshot подтверждение

| Путь | confirm / apply | full_snapshot ack | Где enforced |
|------|-----------------|-------------------|--------------|
| CLI | `--apply` + `--i-understand-apply` | `--full-snapshot` + `--i-understand-full-snapshot` на **APPLY-сессии** | CLI flags → `full_snapshot_acknowledged` → claim |
| Admin API | `confirm=true` + `plan_id` | отдельный `full_snapshot_acknowledged=true` | View → Celery → claim |
| Celery | `plan_id` | `full_snapshot_acknowledged=` | task kwargs → claim |
| `apply_saved_plan` / claim | — | параметр обязателен для `full_snapshot` плана | `_claim_plan_for_apply` |
| `present_only` | apply flags | ack **не** требуется | claim |

`confirm=true` **не** считается full_snapshot ack. Ack **не** наследуется от DRY-RUN.

## 6. Stuck applying

- Авто `applying → ready` **нет**.
- `diagnose_stuck_applying_plan` — plan_id, status, applying_at, timestamps, SyncLog, token presence.
- `manually_resolve_stuck_plan` — только `rejected` | `applied_confirmed` + обязательный note (audit).
- Повторный APPLY при неопределённости запрещён статусом.

## 7. Concurrent claim

Тест: `tests/test_r46_plan_store_concurrent_postgres.py`  
Требует `RINGOO_TEST_POSTGRES=1` + `config.settings.test_postgres` + `DATABASE_URL` на **тестовую** БД.

**Результат в этой среде:** `2 skipped`.  
Локальный PostgreSQL на `:5432` отвечает, но auth `postgres/postgres` отвергнут; Docker Desktop недоступен. Конкурентный тест **не имитировался** на SQLite.

## 8. Тесты

```
tests/test_r46_plan_store.py ................................ 42 passed
D.2.1/D.2.3 regression set (plan/checksum/present_only/block*/stock*/sync_log/…)
  194 passed, 2 skipped (concurrent postgres)
```

Покрыто: forged gate, reuse token/gate, executor без claim, чужой plan_id, helper вне TESTING,
Admin confirm≠FS ack, Celery/CLI FS без ack, present_only без FS ack, stuck не → ready,
reject до записи, rollback mid-apply.

## 9. Оставшиеся риски

1. Concurrent claim не прогнан на PostgreSQL в этой сессии (нужен доступ к test DB).
2. In-process attacker после компрометации worker всё ещё внутри trust boundary.
3. Миграция `0011` — только локально/test; production APPLY не делался.
4. Stuck resolve — ручной ops; автоматического safe recovery нет (намеренно).

## 10. Подтверждения границ

- Production `.env` / migrations APPLY / live 1С write / платежи — не трогались.
- Docker / WireGuard / firewall — не менялись.
- Git add/commit/push/pull/fetch — не выполнялись.
- Beat auto-APPLY — по-прежнему disabled.
- RELEASE 42 leftovers — не менялись.
- D.3 — не начат.
