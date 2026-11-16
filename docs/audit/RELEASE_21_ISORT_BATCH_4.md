# RELEASE 21 — ISORT batch 4 (LOW_RISK blank lines)

**Дата/время:** 2026-11-16 14:20:35 +03:00  
**Основание:** RELEASE 20 = PASS (остаток 72 tracked CI)  
**Вердикт:** **PASS WITH WARNINGS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

Конфиг isort не менялся. R18–R20 сохранены.

---

## 2. Инвентаризация до

| Метрика | Значение |
|---|---:|
| Полный isort fails | **74** |
| Tracked CI | **72** |
| Blank-only кандидаты (ещё не исправлены, не banned) | **29** |

Blank-only **tests** в остатке исчерпаны → партия из простых `apps/*`.

---

## 3. Исправленные файлы (10)

Список: `backend/var/r11/isort_batch4_files.txt`

1. `apps/admin_api/views/users.py`
2. `apps/audit/admin.py`
3. `apps/backups/tests.py`
4. `apps/backups/views.py`
5. `apps/bonus/tests.py`
6. `apps/content/tests.py`
7. `apps/crm/admin.py`
8. `apps/crm/tasks.py` — только убрана лишняя blank внутри одной FIRSTPARTY-секции (`shared_task` / `mask_phone`)
9. `apps/crm/tests.py`
10. `apps/payments/views.py` — blank между Django и DRF

**Обоснование:** все diffs — только пустые строки; `IMPORT_CHANGES=0`.  
Banned / HOLD / tmp / var / migrations — не включались.

---

## 4. Проверки

| Проверка | Результат |
|---|---|
| isort check (партия) | **PASS** |
| Полный isort check | **64** fails |
| Tracked CI remain | **62** |
| `git diff --check` | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| import crm.tasks / payments.views / backups.views / admin users | **OK** |
| pytest bonus+content+crm tests | **PASS** |
| pytest backups (3 crypto) | **FAIL** — см. WARNING |

---

## 5. WARNING — backups cryptography

`apps/backups/tests.py::BackupServiceTests::{encrypt,encrypted_archive,restore_drill}`  
`ModuleNotFoundError: No module named 'cryptography'`

То же ENVIRONMENT BLOCKER, что в RELEASE 12. Diff isort — только blank lines; зависимость не ставилась (запрет).  
Итого по партии: **40 passed, 5 skipped, 3 failed** (все 3 — crypto).

---

## 6. Остаток

| | До | После |
|---|---:|---:|
| All fails | 74 | **64** |
| Tracked CI | 72 | **62** |

Список: `backend/var/r11/isort_remaining_after_batch4.txt`.

Отложено: banned high-risk (celery/settings/signals/orders.views/…), HOLD zero_smoke, MEDIUM/HIGH reorder, tmp.

---

## Вердикт

**PASS WITH WARNINGS** — 10 blank-only исправлены; остаётся **62 tracked CI**; 3 backups-теста блокируются отсутствием `cryptography`.

**Остановка.** Следующая партия / flake8 — после согласования.  
**Никаких коммитов и push.**
