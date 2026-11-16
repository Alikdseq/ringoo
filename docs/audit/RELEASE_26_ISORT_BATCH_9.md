# RELEASE 26 — ISORT batch 9 (DEFERRED review)

**Дата/время:** 2026-11-16 14:44:23 +03:00  
**Основание:** RELEASE 25 = PASS WITH WARNINGS (остаток 22 tracked CI, 9 DEFERRED)  
**Вердикт:** **PASS WITH WARNINGS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

Конфиг / deps / бизнес-логика — без изменений.  
git add / commit / push / pull / fetch / смена ветки / reset / clean / checkout / production / платежи / 1С APPLY / smoke-drill / выполнение connection-скриптов — **не** выполнялись.

---

## 2. Инвентаризация до

| Метрика | Значение |
|---|---:|
| Полный isort fails | **24** |
| Tracked CI | **22** |
| DEFERRED в scope | **9** |

---

## 3. Классификация всех 9 DEFERRED

| Файл | Diff (суть) | Статус | Решение |
|---|---|---|---|
| `test_db_connection.py` | blank stdlib↔django; после `django.setup()` alpha `settings` before `connection` | **SAFE** | исправлен |
| `test_redis_connection.py` | blank stdlib↔django; после setup `settings`/`cache` alpha + blank before `django_redis` | **SAFE** | исправлен |
| `test_celery.py` | `time` в stdlib; после setup `apps.users.tasks` **перед** `config.celery` | **CONDITIONAL** | пропуск: текущий порядок celery-app → tasks может быть намеренным для регистрации |
| `apps/users/tests_security_data.py` | только локальные импорты **внутри метода** (django before apps.audit) | **UNSAFE** | пропуск: запрет in-function без согласования |
| `scripts/b8_018_load_benchmark.py` | blanks + `Decimal` before Product **внутри функций** | **UNSAFE** | in-function + benchmark; не запускался |
| `scripts/block4_offsite_minio_drill.py` | `secrets` before cryptography **внутри** try | **UNSAFE** | in-function + drill + dep `cryptography` |
| `tests/test_concurrency_postgres.py` | top-level pytest↔django **и** in-method `timedelta`/`timezone` | **UNSAFE** | полный fix требует in-function |
| `tests/test_online_cart_retention.py` | top-level blank/PaymentError alpha **и** in-method APIRequestFactory | **CONDITIONAL** | top-level безопасен, но без in-function файл остаётся красным |
| `tests/test_sec005_order_idempotency.py` | top-level blank django↔DRF **и** in-method RequestFactory | **CONDITIONAL** | то же: нужен in-function для полного PASS |

HIGH_RISK / MEDIUM / HOLD / R18–R25 — не трогались.

---

## 4. Исправленные файлы (2)

Список: `backend/var/r11/isort_batch9_files.txt`

1. **`test_db_connection.py`** — blank между `sys` и `django`; после `django.setup()` порядок `django.conf.settings` → `django.db.connection`. Последовательность setup сохранена.
2. **`test_redis_connection.py`** — blank `sys`↔`django`; после setup `settings` → `cache`; blank перед `django_redis`. Setup сохранён.

Обоснование: оба — standalone диагностические скрипты; критичный порядок — только `django.setup()` до Django-импортов; перестановка символов внутри django / секций third-party на поведение не влияет. Скрипты **не** исполнялись.

Примечание: vs `HEAD` в этих файлах уже есть несвязанные quote/whitespace-правки из предыдущих незакоммиченных Black-партий; **вклад R26** — только блок импортов (разделители + порядок).

---

## 5. Проверки

| Проверка | Результат |
|---|---|
| isort check (партия) | **PASS** |
| Полный isort check | **22** fails |
| Tracked CI remain | **20** |
| `git diff --check` (партия) | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| pytest targeted | **N/A** (скрипты, не test-модули) |
| исполнение connection/celery scripts | **не выполнялось** |

---

## 6. Блокеры окружения (без правок)

- отсутствует `cryptography`
- отсутствует `tenacity`
- Promotions validate API → 403
- email status-label тест

---

## 7. Остаток

| | До | После |
|---|---:|---:|
| All fails | 24 | **22** |
| Tracked CI | 22 | **20** |

Артефакты:

- `backend/var/r11/isort_batch9_files.txt`
- `backend/var/r11/isort_remaining_after_batch9.txt`
- `backend/var/r11/isort_remaining_after_batch9_classification.json`

### Классификация остатка (22)

| Вердикт | Count |
|---|---:|
| HIGH_RISK | **9** |
| MEDIUM | **4** |
| DEFERRED | **7** |
| HOLD (`tmp/yk_*.py`) | **2** |

Оставшиеся DEFERRED (7):  
`apps/users/tests_security_data.py`, `scripts/b8_018_load_benchmark.py`, `scripts/block4_offsite_minio_drill.py`, `test_celery.py`, `tests/test_concurrency_postgres.py`, `tests/test_online_cart_retention.py`, `tests/test_sec005_order_idempotency.py`.

---

## Вердикт

**PASS WITH WARNINGS** — из 9 DEFERRED безопасны только 2; исправлены. Остаток **20 tracked CI**. Остальные DEFERRED требуют согласования in-function импортов и/или порядка celery-app.

**Остановка.** MEDIUM / HIGH_RISK / flake8 — только после отдельного согласования.  
**Никаких коммитов и push.**
