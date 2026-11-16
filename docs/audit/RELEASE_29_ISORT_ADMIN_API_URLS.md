# RELEASE 29 — ISORT MEDIUM FIX 2 (`apps/admin_api/urls.py`)

**Дата/время:** 2026-11-16 15:03:14 +03:00  
**Основание:** RELEASE 28 = PASS; RELEASE 27 = SAFE WITH RESTRICTIONS для этого файла  
**Вердикт:** **PASS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

git add / commit / push / pull / fetch / смена ветки / Black / deps / другие файлы / 1С APPLY / платежи / production — **не** выполнялись.

---

## 2. Pre-flight

- Файл уже ` M` vs HEAD (прежний Black/wrap: +3/−1 на path CRM).
- Входил в isort failures.
- isort diff совпал с R27: убрать blank после `backups.views`; merge `.views` + alphabet с `onec_sync` между `managers` и `orders`.

---

## 3. Inventory

| Метрика | До | После |
|---|---:|---:|
| Полный isort fails | **21** | **20** |
| Tracked CI | **19** | **18** |
| `apps/admin_api/urls.py` в fails | да | **нет** |

Артефакты: `backend/var/r11/isort_batch_r29_files.txt`, `isort_remaining_after_r29.txt`, `isort_remaining_after_r29_classification.json`.

---

## 4. Точный список изменений импортов (вклад R29)

1. Удалён blank между `apps.backups.views` и `apps.products.mapping_views`.
2. Две строки:
   - `from .views import content, crm, …, users`
   - `from .views import onec_sync`  
   заменены на один multiline `from .views import (…)`, порядок:  
   `content, crm, dashboard, managers, onec_sync, orders, products, promotions, reports, stock, stores, users`.

`urlpatterns` / `app_name` / path names — **не** менялись вкладом R29.  
Проверка: содержимое файла **ниже** `app_name = "admin_api"` совпало с pre-patch working tree (включая прежний Black wrap CRM path).

`apps/orders/models.py`, `apps/orders/tasks.py`, `apps/users/views.py` — не редактировались в R29.

---

## 5. Проверки

| Проверка | Результат |
|---|---|
| isort `--check-only apps/admin_api/urls.py` | **PASS** |
| Полный isort | **20** fails / **18** tracked CI |
| `git diff --check` | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| import `apps.admin_api.urls` после setup | **OK** (patterns/names/`OneCSyncApplyView` binding; **без** вызова sync/APPLY) |
| `reverse('admin_api:…')` в изоляции | **пропущен** — namespace не зарегистрирован без include в ROOT_URLCONF (ожидаемо; не регресс импорта) |
| pytest `tests/test_admin_api_auth.py` | **PASS** (5) |
| pytest `tests/test_admin_integrity.py` | **PASS** (7) |

1С-синхронизация / APPLY / catalog import / внешние HTTP — **не** запускались.

---

## 6. Контроль diff

- Изменения R28/R29-импортов: только import-блок (см. §4).
- Vs HEAD дополнительно виден **старый** Black wrap `crm-request-update` — сохранён, не откатан.
- Другие файлы R29 не трогал.

---

## 7. Остаток MEDIUM (CONDITIONAL, не трогались)

- `apps/orders/models.py`
- `apps/orders/tasks.py`

---

## Вердикт

**PASS** — `apps/admin_api/urls.py` зелёный по isort; tracked CI **19 → 18**; Django/import/admin_api pytest OK; 1С не вызывалась; Black сохранён; правки только в импортах.

**Остановка.** orders models/tasks — только после отдельного согласования.  
**Никаких коммитов и push.**
