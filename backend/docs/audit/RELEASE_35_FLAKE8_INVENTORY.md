# RELEASE 35 — FLAKE8 FULL INVENTORY + BASELINE CLASSIFICATION

**Дата/время:** 2026-11-16 15:33:40 +03:00  
**Режим:** **READ-ONLY** — код / конфиги линтеров **не** изменялись  
**Вердикт:** **PASS** (инвентаризация завершена)

---

## 1. Branch / HEAD / рабочее дерево

| | Значение |
|---|---|
| Branch | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| flake8 | **7.3.0** (pycodestyle 2.14.0, pyflakes 3.4.0, mccabe 0.7.0) |
| Конфиг | `backend/.flake8` (уже был ` M` до аудита; **не** менялся) |

Working tree до/после аудита: по-прежнему dirty от R8–R34 (Black/isort и др.); аудит добавил только диагностику в `backend/var/r11/` и этот отчёт. Python/app-код аудитом не писался.

`git diff --check`: только CRLF warnings на уже dirty-файлах; маркеров конфликта нет.

---

## 2. Конфиг flake8 (факт)

Из `backend/.flake8`:

- `max-line-length = 120`, `max-complexity = 10`
- **ignore:** E203, E266, **E501**, W503, **F401**, F403, F405  
  → неиспользуемые импорты (F401) и длина строк (E501) **не** входят в inventory
- exclude: venv, migrations, manage.py, settings, …

---

## 3. Полные метрики

| Метрика | Count |
|---|---:|
| Всего сообщений flake8 | **144** |
| Tracked CI | **106** |
| HOLD (`tmp/yk_*`, `scripts/b8_018_zero_smoke.py`) | **37** |
| DIAG (`var/…`) | **1** |
| Прочие untracked app-файлы | **0** |
| Tracked файлов с ошибками | **46** |

Диагностика:

- `backend/var/r11/flake8_r35_full.txt` — полный raw output  
- `backend/var/r11/flake8_r35_tracked_errors.txt` — только tracked  
- `backend/var/r11/flake8_r35_parsed.json` — структурировано  
- `backend/var/r11/flake8_r35_file_classification.json` — риск по файлам  
- `backend/var/r11/flake8_r35_origin_sample.json` — сравнение с HEAD (выборка)

---

## 4. Распределение по кодам

### Все 144

| Код | Count | Смысл |
|---|---:|---|
| C901 | 56 | too complex (mccabe > 10) |
| E402 | 37 | module level import not at top of file |
| E225 | 18 | missing whitespace around operator (почти всё HOLD tmp) |
| F841 | 9 | local variable assigned but never used |
| E231 | 7 | missing whitespace after `,`/`;`/`:`` (HOLD) |
| W291 | 5 | trailing whitespace |
| E226 | 4 | missing whitespace around arithmetic (HOLD) |
| E401 | 2 | multiple imports on one line (HOLD) |
| F811 | 1 | redefinition of unused name |
| F541 | 1 | f-string missing placeholders |
| E305 | 1 | expected 2 blank lines after class/function |
| E121 | 1 | continuation under-indent (HOLD) |
| E701 | 1 | multiple statements on one line (HOLD) |

### Только tracked (106)

| Код | Count |
|---|---:|
| C901 | **56** |
| E402 | **33** |
| F841 | **9** |
| W291 | **5** |
| E305 | 1 |
| F541 | 1 |
| F811 | 1 |

**Вывод:** основной tracked-долг — **сложность (C901)** и **E402 после `django.setup()`** в скриптах; стиль/unused — меньшинство.

---

## 5. Топ tracked-файлов по числу ошибок

| Count | File | Codes |
|---:|---|---|
| 8 | `scripts/b8_018_load_benchmark.py` | C901, E402×6, F541 |
| 8 | `scripts/block4_offsite_minio_drill.py` | E402×8 |
| 7 | `test_db_connection.py` | E402×2, W291×5 |
| 6 | `apps/payments/yookassa_service.py` | C901×6 |
| 6 | `tests/test_int004_int005_yookassa_refund_metadata.py` | F841×6 |
| 5 | `scripts/block4_yookassa_test_refund_drill.py` | C901, E402, F841 |
| 5 | `integrations/onec/orders.py` | C901×5 |
| 4 | `integrations/onec/parser.py` | E402×4 |
| 4 | `apps/payments/services.py` | C901×4 |
| 4 | `test_redis_connection.py` | C901, E402×3 |

Полный список строк: `flake8_r35_tracked_errors.txt`.

---

## 6. Сравнение с HEAD (выборка, доказуемо)

Метод: `flake8` на содержимом `git show HEAD:backend/<file>` vs WT; сравнение **мультимножеств кодов** (не точных номеров строк).

| File | Вердикт | WT | HEAD |
|---|---|---:|---:|
| `apps/orders/views.py` | PRE-EXISTING | 3 C901 | 3 C901 |
| `apps/payments/yookassa_service.py` | PRE-EXISTING | 6 C901 | 6 C901 |
| `apps/payments/services.py` | PRE-EXISTING | 4 C901 | 4 C901 |
| `integrations/onec/importer.py` | PRE-EXISTING | 3 C901 | 3 C901 |
| `apps/users/views.py` | PRE-EXISTING | 1 C901 | 1 C901 |
| `apps/backups/offsite.py` | PRE-EXISTING | 2 C901 | 2 C901 |
| `tests/test_int004_…refund_metadata.py` | PRE-EXISTING | 6 F841 | 6 F841 |
| `scripts/b8_018_load_benchmark.py` | PRE-EXISTING | 8 | 8 |
| `apps/admin_api/views/products.py` | PRE-EXISTING | 1 C901 | 1 C901 |
| `apps/products/services/bulk_import.py` | PRE-EXISTING | C901+E305 | same |
| `test_celery.py` | **DECREASED_VS_HEAD** | E402×2 | E402×2 + W293×9 |
| `scripts_sentry_smoke.py` | **DECREASED_VS_HEAD** | C901+E402 | + W293×10 |

Файлы без flake8 на HEAD и WT в выборке (`bonus/signals`, `config/urls`, `celery`, `cart/views`): ошибок flake8 **нет** (isort-правки не породили flake8 в этих файлах).

Массового роста flake8 от Black/isort **не** видно; часть W293 даже уменьшилась. Происхождение прочих файлов вне выборки: **UNKNOWN** без пофайлового прогона.

---

## 7. Классификация рисков (46 tracked files)

| Класс | Files | Errors (approx) |
|---|---:|---:|
| SAFE | 3 | 8 |
| SAFE WITH RESTRICTIONS | 8 | 40 |
| CONDITIONAL | 25 | 31 |
| HIGH_RISK | 10 | 27 |
| HOLD | (не tracked CI) | 37 в full |

### SAFE (первый пакет R36)
- `tests/test_int004_int005_yookassa_refund_metadata.py` — F841×6  
- `apps/users/tests_security_data.py` — F841×1  
- `tests/test_func007_bonus_flag.py` — F841×1  

Исправление: убрать/использовать неиспользуемые локальные переменные; не менять логику assert’ов.

### SAFE WITH RESTRICTIONS
Скрипты с **E402** после `django.setup()` / trailing ws:
- `test_db_connection.py` (W291 + E402)
- `test_redis_connection.py`, `test_celery.py`, `scripts_sentry_smoke.py`
- `scripts/block4_offsite_minio_drill.py`, `b8_018_load_benchmark.py`, `b8_018_rerun_dryrun.py`, `block4_yookassa_test_refund_drill.py`

Ограничения: не запускать drill/benchmark/sentry smoke; E402 часто **намеренный** (import after setup) — либо `# noqa: E402` точечно (только после отдельного разрешения на noqa), либо рефакторинг структуры; **не** переносить импорты выше `django.setup()`.

### CONDITIONAL
Почти все одиночные **C901** в admin/products/stores/backups/clients + `integrations/onec/parser.py` E402 + `bulk_import` E305.  
Требуют рефакторинга сложности или осознанного raise complexity / точечного ignore — не «быстрый fix».

### HIGH_RISK (C901 / F811 на критичных путях)
- `apps/orders/views.py` (C901×3)
- `apps/payments/yookassa_service.py` (C901×6)
- `apps/payments/services.py` (C901×4)
- `apps/payments/eligibility.py` (C901 + **F811**)
- `apps/orders/services/transitions.py`, `apps/cart/checkout_clear.py`
- `apps/users/views.py`
- `integrations/onec/{importer,orders,catalog_sync}.py`

Не трогать без отдельного аудита и сильных тестов (оплата / заказы / 1С / auth).

### Зоны внимания
| Зона | Наблюдение |
|---|---|
| Импорты / циклы | E402 в скриптах и `onec/parser.py`; F401 скрыт ignore |
| Django init | E402 после setup — ожидаемо |
| Celery | `test_celery.py` только E402; C901 в task bodies нет в remain |
| Платежи | главный C901-кластер |
| Заказы/корзина | C901 в views/transitions/checkout_clear |
| 1С | C901 importer/orders/catalog_sync; E402 parser |
| Auth | C901 `users/views.py` |
| Concurrency tests | flake8-ошибок в `test_concurrency_postgres` **нет** |

---

## 8. Приоритет следующих пакетов (не выполнять сейчас)

1. **R36 SAFE F841 tests** — 3 файла / 8 ошибок; targeted pytest этих тестов.  
2. **R37 script hygiene** — W291 в `test_db_connection.py`; F541 в load_benchmark; E305 в bulk_import (без запуска drills).  
3. **R38 E402 policy** — отдельное решение: noqa после setup vs реструктуризация скриптов (нужен ACK на noqa).  
4. **R39 C901 non-critical** — admin_api/products/stock, backups, catalog commands (с тестами).  
5. **R40+ HIGH_RISK C901** — payments/orders/onec/users только после аудита.  
6. **Не чинить без разрешения:** HOLD tmp/zero_smoke; ослабление `.flake8`; массовый noqa.

Атомарность: ≤5–8 файлов или один класс кода за пакет.

---

## 9. Ограничения и блокеры

- F401/E501 **не видны** из-за текущего ignore — «полный» CI flake8 ≠ полный pyflakes unused-import.  
- C901=56 доминирует: зелёный flake8 без рефакторинга или изменения `max-complexity` / per-file-ignores **маловероятен**.  
- Известные env-блокеры тестов (`cryptography`, `tenacity`, …) к flake8 inventory не относятся.  
- isort remain (`test_celery.py` + HOLD) ортогонален flake8.

---

## 10. Подтверждения

- Python-код, `.flake8`, зависимости — **не** менялись этим релизом.  
- Пользовательские dirty-изменения сохранены.  
- HOLD не предлагаются к правке.  
- Коммитов / push / смены ветки нет.

**Остановка.** Следующий шаг — RELEASE 36 (SAFE F841), только после согласования.
