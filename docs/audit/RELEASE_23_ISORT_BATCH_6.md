# RELEASE 23 — ISORT batch 6 (LOW_RISK)

**Дата/время:** 2026-11-16 14:28:35 +03:00  
**Основание:** RELEASE 22 = PASS WITH WARNINGS (остаток 52 tracked CI)  
**Вердикт:** **PASS WITH WARNINGS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

Конфиг isort / Black / flake8 / mypy / deps — без изменений.  
git add / commit / push / pull / fetch / смена ветки — не выполнялись.

---

## 2. Инвентаризация до

Источник: `backend/var/r11/isort_remaining_after_batch5.txt` + повторный полный `python -m isort --check-only --diff .`.

| Метрика | Значение |
|---|---:|
| Полный isort fails | **54** |
| Tracked CI | **52** |
| Кандидаты партии (≤10 LOW_RISK) | **10** |

Tracked status и CI scope перепроверены; старые списки без повторной проверки не использовались.

---

## 3. Исправленные файлы (10)

Список: `backend/var/r11/isort_batch6_files.txt`

| # | Файл | Тип правки | Обоснование безопасности |
|---|---|---|---|
| 1 | `apps/users/tests_legal.py` | blank-only (django ↔ DRF) | тестовый модуль; только разделитель секций импортов |
| 2 | `apps/wishlist/admin.py` | blank-only (django ↔ local) | простой admin; регистрация моделей не зависит от blank |
| 3 | `config/throttling.py` | blank-only (django ↔ DRF) | mixin/throttle rates; нет signals/tasks; init без side effects на импорт-порядок |
| 4 | `integrations/email_service.py` | blank-only (stdlib ↔ django) | сервисные функции; импорты без циклов/signals |
| 5 | `integrations/maps_service.py` | blank-only (django ↔ tenacity) | порядок third-party после django; логика не менялась |
| 6 | `integrations/onec/inbound_views.py` | blank-only (django ↔ DRF) | view-модуль; без importer/APPLY; HMAC/permission импорты в той же группе |
| 7 | `integrations/tests_email_service.py` | blank-only (убран blank apps↔integrations) | оба FIRSTPARTY; безопасное слияние секции |
| 8 | `integrations/tests_maps_service.py` | blank-only (убран blank apps↔integrations) | оба FIRSTPARTY; безопасное слияние секции |
| 9 | `scripts/block4_yookassa_test_refund_drill.py` | blank-only | blank после docstring / после `django.setup()` **сохранён порядок** setup → YooKassaClient; drill не запускался |
| 10 | `tests/test_admin_mfa.py` | blank + local alpha | blank django↔DRF; локально `totp` перед `TOTPDevice` (оба django_otp, без side effects) |

Banned / HOLD / tmp / var / migrations / R18–22 files — не включались.  
HIGH_RISK без отдельного анализа — не включались.

В части файлов в том же diff видны свёртки длинных строк вне блока импортов (как в R18–22 working tree / Black-compatible wrap); сигнатуры и бизнес-логика не менялись, импорты не удалялись и не переносились в/из функций.

---

## 4. Проверки

| Проверка | Результат |
|---|---|
| isort check (партия) | **PASS** (`BATCH_CHECK=0`) |
| Полный isort check | **44** fails |
| Tracked CI remain | **42** |
| `git diff --check` | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| import `config.throttling`, `wishlist.admin`, `onec.inbound_views`, `email_service` | **OK** |
| pytest `apps/users/tests_legal.py` + `tests/test_admin_mfa.py` | **PASS** (13) |
| pytest `integrations/tests_email_service.py` | **1 FAIL** — статусный текст (см. §5) |
| pytest / import `integrations/tests_maps_service` / `maps_service` | **BLOCKED** — нет `tenacity` (см. §5) |
| smoke / payments / 1С APPLY / migrate | **не запускались** |

---

## 5. WARNING — известные блокеры окружения

Зафиксированы, **не исправлялись**, зависимости **не устанавливались**:

1. **`cryptography` отсутствует** — backups-тесты (как R21).
2. **Promotions validate API → 403** — как R14/R22; в эту партию promotions-тесты не входили.
3. **`tenacity` отсутствует** — блокирует import/pytest `integrations.maps_service` / `tests_maps_service` в текущем venv.
4. **`TestSendOrderStatusChange::test_sends_with_old_and_new_status`** — AssertionError: ожидает `'Подтверждён'`, в письме `'В обработке'`. Не связано с перестановкой импортов (копирайт/лейблы статусов); логику не трогали.

---

## 6. Остаток

| | До | После |
|---|---:|---:|
| All fails | 54 | **44** |
| Tracked CI | 52 | **42** |

Артефакты:

- `backend/var/r11/isort_batch6_files.txt`
- `backend/var/r11/isort_remaining_after_batch6.txt`
- `backend/var/r11/isort_remaining_after_batch6_classification.json`

### Классификация остатка (44)

| Вердикт | Count |
|---|---:|
| HIGH_RISK (banned) | **9** |
| HOLD (`tmp/yk_*.py`) | **2** |
| DEFERRED | **33** |

### MEDIUM / HIGH / HOLD (отложено)

- **HIGH/banned:** `config/celery.py`, `config/settings/base.py`, `config/urls.py`, `config/api_urls.py`, `apps/bonus/signals.py`, `apps/orders/views.py`, `apps/cart/views.py`, `integrations/onec/importer.py`, `scripts_sentry_smoke.py`
- **HOLD:** `scripts/b8_018_zero_smoke.py` (по-прежнему вне партии; в текущем remain isort **не** фигурирует)
- **tmp HOLD:** `tmp/yk_net_probe.py`, `tmp/yk_ro_probe.py`
- **DEFERRED:** остальные tracked CI с non-trivial reorder / app init risk — без отдельного анализа не трогались

---

## Вердикт

**PASS WITH WARNINGS** — партия 6 (10 LOW_RISK) зелёная по isort/Django/legal+mfa; остаётся **42 tracked CI**; env-блокеры `cryptography` / `tenacity` / promotions 403 / email status-label зафиксированы без правок.

**Остановка.** Следующая партия / flake8 — после согласования.  
**Никаких коммитов и push.**
