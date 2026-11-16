# RELEASE 28 — ISORT MEDIUM FIX 1 (`apps/users/views.py`)

**Дата/время:** 2026-11-16 15:00:41 +03:00  
**Основание:** RELEASE 27 = AUDIT COMPLETE (`SAFE WITH RESTRICTIONS`)  
**Вердикт:** **PASS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

git add / commit / push / pull / fetch / смена ветки / Black / deps / другие isort-файлы / production / платежи / 1С — **не** выполнялись.

---

## 2. Inventory

| Метрика | До | После |
|---|---:|---:|
| Полный isort fails | **22** | **21** |
| Tracked CI | **20** | **19** |
| `apps/users/views.py` в fails | да | **нет** |

Артефакты: `backend/var/r11/isort_batch_r28_files.txt`, `isort_remaining_after_r28.txt`, `isort_remaining_after_r28_classification.json`.

---

## 3. Точный diff (вклад R28)

Только top-level imports (surgical replace блока до `logger = ...`). Тело файла после `logger` **байтно совпало** с pre-patch working tree.

### Изменения импортов

1. `from django.db import OperationalError, ProgrammingError, transaction`  
   (отдельный `from django.db import transaction` после simplejwt удалён).
2. Blank между Django и DRF.
3. DRF merge/alpha:  
   `serializers, status`; `AuthenticationFailed, ValidationError`;  
   `generics` в DRF-группе; порядок permissions/response/views/simplejwt сохранён по isort.
4. Relative: `.security_logging` **перед** `.serializers`.

### Не изменялось

- декораторы `csrf_exempt` / `method_decorator`;
- классы/методы auth/JWT/MFA/token/register/refresh/logout;
- API-сигнатуры;
- импорты внутри функций;
- `apps/admin_api/urls.py`, `apps/orders/models.py`, `apps/orders/tasks.py`.

### Сохранность прежних Black/wrap правок

Файл до R28 уже был ` M` vs HEAD (Black). Примеры pre-existing wrap в теле (не откатывались) по-прежнему в working tree, напр. свёртка `raw = attrs.get(...)` и `groups = list(user.groups.filter(...))`.  
`git diff` vs HEAD смешивает старый Black + новый import-блок; вклад R28 ограничен импортами (проверено сравнением post-`logger` с pre-patch).

---

## 4. Проверки

| Проверка | Результат |
|---|---|
| isort `--check-only apps/users/views.py` | **PASS** |
| Полный isort | **21** fails / **19** tracked CI |
| `git diff --check` (файл) | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| `import apps.users.views` после setup | **OK** |
| pytest legal + admin_mfa + sec009 + admin_api_auth | **PASS** (23) |

Известные env-блокеры (`cryptography`, `tenacity`, promotions 403, email status-label) в прогон не входили / не чинились.

---

## 5. Остаток MEDIUM (не трогались)

- `apps/admin_api/urls.py` — SAFE WITH RESTRICTIONS (следующий кандидат)
- `apps/orders/models.py` — CONDITIONAL (in-function)
- `apps/orders/tasks.py` — CONDITIONAL (in-function)

---

## Вердикт

**PASS** — `apps/users/views.py` зелёный по isort; tracked CI **20 → 19**; auth/MFA/legal pytest зелёные; старый Black сохранён; посторонних правок нет.

**Остановка.** `admin_api/urls.py` / orders models|tasks — не трогать без нового согласования.  
**Никаких коммитов и push.**
