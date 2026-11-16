# RELEASE 10 — Инвентаризация isort (после RELEASE 8)

**Дата:** 2026-11-16  
**Проект:** `C:\ringoo`  
**Основание:** RELEASE 8 = PASS WITH WARNINGS; RELEASE 9 = PASS  
**Вердикт:** **PASS**

---

## 1. Branch и HEAD

| | Значение |
|---|---|
| Branch | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| BASE | `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8` |

### Рабочее дерево (ожидаемое dirty-состояние)

- **RELEASE 8 (конфиги):** `backend/.flake8`, `backend/.isort.cfg`, `backend/pyproject.toml`
- **RELEASE 9 (21 py):** Black-форматирование RELEASE 1–3 (список в R9)
- Иных правок исходников в R10 **не делалось**

---

## 2. Версия isort

`7.0.0` (`backend/venv`, `python -m isort`)

---

## 3. Подтверждение загрузки конфигурации

Проверка через `isort.settings.Config` + `place_module`:

| Проверка | Результат |
|---|---|
| Конфиг загружается | **OK** (без ERROR/ValueError) |
| `.isort.cfg` ↔ `[tool.isort]` | Согласованы: одни `sections`, `known_*`, `skip` |
| `profile` | `black` |
| `sections` | `FUTURE, STDLIB, DJANGO, THIRDPARTY, FIRSTPARTY, LOCALFOLDER` |
| `sentry_sdk` | `place_module → THIRDPARTY` |
| `django` | `DJANGO` |
| skip venv | `venv`, `.venv`, `env` + skip_glob |

Конфликт конфигураций **не обнаружен**. Режим записи не использовался.

Диагностика: `backend/var/r10/isort_config_probe.txt`.

---

## 4. Полный объём нарушений (текущее WT)

Команда (READ-ONLY):

```text
python -m isort --check-only --diff .
```

| Метрика | Значение |
|---|---:|
| Exit | 1 |
| Файлов с нарушениями (текущее дерево) | **116** |
| Из них tracked | **114** |
| Полный diff | `backend/var/r10/isort_check_diff.txt` |
| Список fails | `backend/var/r10/fails_current.txt` |

---

## 5. BASE / HEAD сравнение

Без checkout/switch: `git archive --format=zip` → `%TEMP%\ringoo-r10-{base,head}\`, поверх наложены **исправленные** конфиги R8 (чтобы сравнивать долг при рабочей конфигурации).

| Состояние | Fails (isort 7 + fixed config) |
|---|---:|
| BASE `b3a9db4` | **105** |
| HEAD commit `fcc23d0` (clean tree) | **116** |
| Текущее WT (HEAD + R8/R9 dirty) | **116** (+ `tmp/*` vs clean HEAD) |

Δ HEAD−BASE = **+11** файлов с нарушениями при той же fixed-конфигурации.

Артефакты: `var/r10/fails_base.txt`, `fails_head_commit.txt`, `isort_*_stderr_clean.txt`.

### Ограничение сравнения

Сравнение выполнено на временных zip-деревьях с **overlay R8-конфигов**. Это намеренно: цель — объём нарушений *после* починки конфига, а не воспроизведение старого config-crash. Относительно «сырого» BASE без R8-конфига isort 7 ранее падал на `THIRD_PARTY` — тот режим здесь не используется.

---

## 6. Таблица групп (текущее WT)

| Группа | Всего файлов с isort-fails | Нарушения isort | Примечание |
|---|---:|---:|---|
| **A — RELEASE 1–3** (tracked ∩ `BASE..HEAD`) | 33 | 33 | из них **9 new vs BASE**, **24** уже на BASE |
| **B — остальные tracked** | 81 | 81 | в основном предсуществующий долг (~BASE) |
| **C — untracked / HOLD / tmp** | 2 | 2 | `tmp/yk_*.py`; HOLD `zero_smoke` в fails **не** попал |
| **Итого** | 116 | 116 | |

### 6.1 Группа A — полный список + происхождение

#### A-NEW (нет в BASE fails / новые относительно BASE) — 9

| Файл | Суть предложения isort | Safety |
|---|---|---|
| `apps/products/admin.py` | перестановка внутри multi-import (`archive_product`, …) | MANUAL_REVIEW |
| `integrations/onec/importer.py` | локальный import: `build_issue_counts, partition_issues` | MANUAL_REVIEW |
| `scripts/b8_018_load_benchmark.py` | blank lines вокруг `from decimal import Decimal` после `django.setup()` | **MANUAL** |
| `tests/test_fix_pack_a_guest_success.py` | blank line между секциями | AUTO_OK |
| `tests/test_fix_pack_b_order_cancellation.py` | blank line между секциями | AUTO_OK |
| `tests/test_onec_block3_series_cart.py` | blank line между секциями | AUTO_OK |
| `tests/test_onec_block5_security_integrity.py` | blank line между секциями | AUTO_OK |
| `tests/test_onec_block6_performance.py` | blank + позиция `django.core.cache` | MANUAL_REVIEW |
| `tests/test_onec_stock_reconciliation.py` | alphabetical: `CONFIRMED_WAREHOUSE_IDS, CONFIRMED_WAREHOUSES` | MANUAL_REVIEW |

#### A-OLD (уже failing на BASE, файл в RELEASE range) — 24

| Файл | Суть предложения isort | Safety |
|---|---|---|
| `apps/admin_api/views/orders.py` | blank lines между секциями | AUTO_OK |
| `apps/admin_api/views/products.py` | blank line | AUTO_OK |
| `apps/admin_api/views/stock.py` | blank line | AUTO_OK |
| `apps/cart/tests.py` | `Stock, Store`; порядок `.services` | MANUAL_REVIEW |
| `apps/cart/views.py` | порядок символов в multi-import serializer | MANUAL_REVIEW |
| `apps/orders/tests.py` | `Stock, Store`; порядок local imports | MANUAL_REVIEW |
| `apps/orders/views.py` | blank вокруг **локального** `CartSerializer` import | MANUAL_REVIEW |
| `apps/products/views.py` | alphabetical в `catalog_filters` import | AUTO_LIKELY |
| `apps/stores/admin.py` | `Manager, Stock, Store, StoreImage` | AUTO_LIKELY |
| `apps/stores/serializers.py` | то же | AUTO_LIKELY |
| `apps/stores/tests.py` | blank + `Stock, Store` | AUTO_LIKELY |
| `apps/stores/views.py` | `ManagerRating` + models alphabetical | MANUAL_REVIEW |
| `apps/users/tests.py` | blank line | AUTO_OK |
| `tests/test_admin_integrity.py` | blank line | AUTO_OK |
| `tests/test_block8_catalog_guards.py` | лишняя blank | AUTO_OK |
| `tests/test_func001_expire_yookassa_sync.py` | blank line | AUTO_OK |
| `tests/test_func002_func009_cancel_policy.py` | blank line | AUTO_OK |
| `tests/test_int001_int002_order_fsm.py` | лишняя blank | AUTO_OK |
| `tests/test_order_repay.py` | blank line | AUTO_OK |
| `tests/test_payment_security.py` | blank line | AUTO_OK |
| `tests/test_sber_payments.py` | blank line | AUTO_OK |
| `tests/test_sec003_cancel_releases_stock.py` | blank line | AUTO_OK |
| `tests/test_sec005_order_idempotency.py` | blank вокруг локального `RequestFactory` | MANUAL_REVIEW |
| `tests/test_sec006_guest_access_token.py` | blank line | AUTO_OK |

### 6.2 Группа B — остальные tracked (81)

Полный список: `backend/var/r10/group_b.txt`.

Включает в т.ч. чувствительные точки (для будущего fix-этапа, **не** для автобез проверки):

- `config/celery.py` — Celery / autodiscover risk  
- `apps/bonus/signals.py` — registration / side effects  
- `config/settings/base.py`, `config/urls.py`, `config/api_urls.py`  
- `apps/users/views.py`, `apps/payments/views.py`, …  
- `scripts_sentry_smoke.py` — `django.setup()` + `sentry_sdk`

Почти все B пересекаются с BASE fails → **старый долг**.

### 6.3 Группа C (2)

- `tmp/yk_net_probe.py`
- `tmp/yk_ro_probe.py`

`scripts/b8_018_zero_smoke.py` (HOLD, untracked) — в текущем isort-скане нарушений не зафиксирован / не включается в план.

---

## 7. Кандидаты на автоматическое форматирование (только согласование)

**Потенциально AUTO (Group A):** 18 `AUTO_OK` + 4 `AUTO_LIKELY` = **22 файла**  
Критерий: в основном blank lines между секциями или безопасная alphabetical-перестановка имён в том же import-statement; без `django.setup`, без изменения набора импортов.

Не является разрешением запускать isort write — только инвентаризационная рекомендация.

## 8. Требуют ручной проверки перед любым isort write

| Файл | Почему |
|---|---|
| `scripts/b8_018_load_benchmark.py` | `django.setup()`; локальные импорты после setup |
| `integrations/onec/importer.py` | локальный import reporting (возможный цикл) |
| `apps/orders/views.py` | локальный import `CartSerializer` |
| `apps/cart/views.py`, `apps/cart/tests.py` | reorder + local structure |
| `apps/orders/tests.py` | reorder local/tasks |
| `apps/products/admin.py` | admin registration imports |
| `apps/stores/views.py` | cross-app `ManagerRating` |
| `tests/test_onec_block6_performance.py` | Django cache import placement |
| `tests/test_onec_stock_reconciliation.py` | warehouse_map symbols |
| `tests/test_sec005_order_idempotency.py` | локальный `RequestFactory` |

Из **Group B** (вне RELEASE scope, но высокий риск): `config/celery.py`, `apps/bonus/signals.py`, `config/settings/base.py`, `scripts_sentry_smoke.py`.

Вывод о безопасности **не** делается только по наличию diff: учитывались локальные импорты, `django.setup`, admin/signals/celery.

---

## 9. Регрессионные проверки (read-only)

| Проверка | Результат |
|---|---|
| `git diff --check` | PASS (0) |
| `manage.py check` (`config.settings.test`) | PASS — no issues |
| `makemigrations --check --dry-run` | PASS — No changes detected |

Массовое форматирование / тесты с записью в пользовательскую БД / APPLY — **не запускались**.

---

## 10. Git status и отсутствие изменений исходников R10

HEAD неизменен: `fcc23d001ddea397e152adde4ea4c86f25ff74e3`, branch `main`.

Dirty tree = только наследие R8 + R9 + пользовательские untracked (отчёты/docx/`промпт.txt`/HOLD).

**Новые артефакты R10 (вне Git-истории кода):**

- `docs/audit/RELEASE_10_ISORT_INVENTORY.md` (этот отчёт)
- `backend/var/r10/*` (диагностика)

Исходники / конфиги / зависимости **R10 не менял**.

---

## 11. Краткие выводы для следующего этапа

1. Конфиг isort 7 после R8 **рабочий**; inventory возможен.
2. Фактический долг на WT: **~116** файлов.
3. Из них RELEASE-связанных: **33**; genuinely new vs BASE: **9**.
4. Основной долг (**~105** на BASE) — вне RELEASE; чинить целиком = отдельное решение.
5. После R9 Black часть файлов получила/сохранила isort blank-line drift (isort хочет пустые строки между секциями) — ожидаемо совместимо чинится isort `--profile black`, но только точечно после согласования.

---

## Вердикт

**PASS** — инвентаризация завершена, конфигурация isort загружается корректно, BASE/HEAD сравнены через временные zip-деревья, исходники не изменялись.

**Остановка.** Исправление isort (write) — только после отдельного согласования.  
**Никаких коммитов и push.**
