# RELEASE 27 — ISORT MEDIUM audit (READ-ONLY)

**Дата/время:** 2026-11-16 14:47:57 +03:00  
**Основание:** RELEASE 26 = PASS WITH WARNINGS (остаток 20 tracked CI, 4 MEDIUM)  
**Режим:** **строго READ-ONLY** — исходники MEDIUM-файлов **не** изменялись  
**Вердикт аудита:** **AUDIT COMPLETE — WAIT FOR APPROVAL**

---

## 1. Branch / HEAD / inventory

| | Значение |
|---|---|
| Branch | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 |
| Полный isort fails | **22** |
| Tracked CI | **20** |

Источник остатка: `backend/var/r11/isort_remaining_after_batch9.txt` / `*_classification.json`.

Команды: только `isort --check-only --diff` (без записи), чтение исходников, `git status`/`git diff` (read-only).  
Black / isort write / pytest с внешними действиями / git mutate / deps — **не** запускались.

### Примечание о working tree

Все четыре файла уже помечены ` M` относительно HEAD из‑за **ранее незакоммиченных** Black/wrap правок (тело файлов), **не** из‑за этого аудита. Ниже isort-diff считается относительно **текущего содержимого на диске**.

Подтверждение неизменности аудитом: статус ` M` сохраняется; R27 код не писал.

---

## 2. Сводка классификации

| Файл | Итоговый статус | Можно без in-function? |
|---|---|---|
| `apps/admin_api/urls.py` | **SAFE WITH RESTRICTIONS** | Да (только top-level) |
| `apps/orders/models.py` | **CONDITIONAL** | **Нет** — failure только in-function |
| `apps/orders/tasks.py` | **CONDITIONAL** | **Нет** — failure только in-function |
| `apps/users/views.py` | **SAFE WITH RESTRICTIONS** | Да (только top-level) |

Ни один файл не получил чистый **SAFE** без ограничений: urls меняет порядок загрузки `onec_sync`; users — auth-критичный модуль; models/tasks требуют in-function по политике R25–R26.

---

## 3. `apps/admin_api/urls.py`

### A. Isort diff (точный смысл)

1. **Удаление blank** между блоком `apps.backups.views` и `apps.products.mapping_views` (оба FIRSTPARTY `apps.*`).
2. **Объединение** двух строк:
   - `from .views import content, crm, dashboard, managers, orders, products, promotions, reports, stock, stores, users`
   - `from .views import onec_sync`  
   → один multiline `from .views import (...)` с **алфавитным** порядком, где `onec_sync` встаёт между `managers` и `orders`.

Типы изменений: blank-separator + merge import-строк + перестановка имён в одной группе.  
In-function: **нет**.

### B. Зависимости / side effects

- `apps/admin_api/views/__init__.py` — пустой.
- View-модули (`content`, `orders`, `onec_sync`, …) при импорте: DRF/views + models + `permissions`; **не** импортируют `admin_api.urls`.
- `permissions.py`: константы групп + классы Permission; импорт `admin_mfa` — без URL cycle.
- `onec_sync` тянет `integrations.onec.catalog_sync` и `apps.orders.models.OneCInboundEvent` — тяжёлый firstparty, но без обратной связи на urls.
- `AppConfig.ready()` / signals в orders/users apps для этого пути не задействованы напрямую urlpatterns.

**Изменение поведения при apply:** порядок *загрузки* view-модулей. Сейчас `onec_sync` импортируется **после** всех остальных listed modules; после isort — **раньше** (`… managers → onec_sync → orders …`). На `urlpatterns` это не влияет (имена уже связаны), риск — только гипотетический side effect при import-time `onec_sync`/`catalog_sync` до соседних admin views. Цикла urls↔views не найдено.

### C. Вердикт

**SAFE WITH RESTRICTIONS**

- **Можно менять:** blank между backups/products; merge `.views` в один sorted import.
- **Нельзя менять:** `urlpatterns`, имена path, закомментированные bonus routes, импорты backups/returns/mapping_views (кроме blank/форматирования, которое предлагает isort).
- **Безопасный вариант:** принять diff isort целиком для этого файла.
- **Проверки после fix:** `import apps.admin_api.urls` после `django.setup()`; Django `check`; targeted admin_api auth/URL tests (без APPLY 1С).

---

## 4. `apps/orders/models.py`

### A. Isort diff

Единственное изменение — **внутри** `_generate_order_number()`:

```text
# было
from django.utils import timezone
import random

# будет
import random

from django.utils import timezone
```

Тип: in-function — stdlib `random` перед Django + blank.  
Top-level (`uuid`, `Decimal`, `django.conf`, `django.db.models`) — **уже корректен**; отдельного top-level fix **нет**.

### B. Зависимости / side effects

- Локальные импорты откладывают загрузку до вызова генератора номера (default callable / save path).
- Оба символа нужны только для строк `timezone.now()` / `random.randint`; побочных эффектов у `import random` и `django.utils.timezone` при таком использовании нет.
- Перенос `random` на module level **не** требуется для isort и **не** рекомендован (расширяет поверхность импорта models).

### C. Вердикт

**CONDITIONAL**

- Технически перестановка in-function **низкий риск** (stdlib ↔ django, без циклов).
- По процессу R25–R26: **in-function без отдельного согласования запрещены**.
- **Нельзя** «починить файл», не трогая импорты в функции.
- **Нельзя менять без согласования:** тело `_generate_order_number`, перенос импортов на module level, модели/FSM поля.
- **Проверки после возможного fix:** unit на генерацию `order_number`; создание Order в тестах; models import.

---

## 5. `apps/orders/tasks.py`

### A. Isort diff

Единственное изменение — **внутри** `send_order_notifications`:

```text
# было
from .models import Order
from integrations.email_service import send_order_confirmation

# будет
from integrations.email_service import send_order_confirmation

from .models import Order
```

Тип: in-function — absolute firstparty перед relative + blank.  
Другие tasks (`sync_order_to_onec_task`, `cancel_order_in_onec_task`) и top-level (`shared_task`, `timezone`) isort **не** трогает.

### B. Зависимости / side effects

- Top-level: `config.optional_task.shared_task` — регистрация задач **не** меняется этим diff.
- `integrations.email_service`: logging/django mail/templates/`config.pii`; **не** импортирует `apps.orders.models` / `orders.tasks` на уровне модуля; `send_order_confirmation(order)` принимает экземпляр duck-typed.
- Цикл tasks→email→tasks: **не** обнаружен.
- Оба импорта выполняются при *исполнении* Celery-задачи (apps already ready), не при import модуля tasks.

Риск изменения порядка: минимальный (email до Order vs Order до email) — оба чистые на import.

### C. Вердикт

**CONDITIONAL**

- Технически **низкий риск**, но это **in-function** → нужно явное согласование.
- Top-level-only исправление **невозможно** (isort failure только здесь).
- **Нельзя менять без согласования:** декораторы `@shared_task`, top-level порядок `optional_task`, тела 1С sync tasks, перенос email/Order на module level.
- **Проверки после fix:** импорт `apps.orders.tasks`; unit/mock на `send_order_notifications` (без реальной почты/1С APPLY).

---

## 6. `apps/users/views.py`

### A. Isort diff (top-level only)

1. **Merge** `transaction` в `from django.db import OperationalError, ProgrammingError, transaction` (сейчас `transaction` отдельной строкой **после** simplejwt).
2. **Blank** между блоком Django и DRF.
3. **Слияние/алфавит DRF:**  
   `serializers`+`status`; `AuthenticationFailed`+`ValidationError`; `generics` поднимается к DRF-группе; убираются дублирующие разрозненные строки.
4. **Relative alpha:** `security_logging` **перед** `serializers`.

In-function в isort-diff: **нет**.

### B. Зависимости / side effects

- `transaction` используется позже (`transaction.atomic()` ~стр. 613); ранний import `django.db.transaction` side-effect свободен.
- DRF/simplejwt: стандартные библиотечные импорты; классы views объявляются **после** полного блока импортов → перестановка имён в import-блоке не меняет порядок выполнения class body.
- `.security_logging`: logging + `config.pii` + `.services` (get_client_ip/normalize_phone) — без регистрации URL/signals.
- `.serializers` / `.jwt_cookies` / `.admin_mfa` / `merge_guest_cart_into_user`: существующие зависимости; обратных импортов `apps.users.views` из этих модулей в ходе аудита не найдено.
- Auth-критичность высокая (JWT, csrf_exempt, MFA), поэтому даже при нейтральном diff нужен регрессионный прогон.

### C. Вердикт

**SAFE WITH RESTRICTIONS**

- **Можно менять:** ровно то, что показывает isort (django/DRF merge + blank + relative alpha).
- **Нельзя менять:** декораторы `csrf_exempt`/`method_decorator`, логику token/register/refresh/logout/MFA, перенос импортов в методы, сигнатуры API.
- **Проверки после fix:** import `apps.users.views`; Django check; targeted auth/JWT/MFA/legal tests (без внешних платежей).

---

## 7. Рекомендуемый следующий этап (после согласования)

| Приоритет | Файл | Действие | Ожидаемый эффект на tracked CI |
|---|---|---|---|
| 1 | `apps/users/views.py` | принять isort top-level | −1 |
| 2 | `apps/admin_api/urls.py` | принять isort top-level | −1 |
| 3 | `apps/orders/models.py` | только после ACK на in-function | −1 |
| 4 | `apps/orders/tasks.py` | только после ACK на in-function | −1 |

Не смешивать с HIGH_RISK / flake8 в том же шаге.

Обязательные проверки на этапе fix (когда будет разрешено писать код):

1. isort check партии / полный isort / tracked CI count  
2. `git diff --check`  
3. Django `check` + `makemigrations --check --dry-run`  
4. targeted pytest (auth / admin_api / orders notifications mocks)  
5. безопасный import модулей  

Известные env-блокеры (`cryptography`, `tenacity`, promotions 403, email status-label) — не трогать.

---

## 8. Риски и ограничения

- **urls:** единственный содержательный риск — более ранний import `onec_sync` (и транзитивно catalog_sync).
- **models/tasks:** без ослабления запрета на in-function isort по ним **не** зеленеет.
- **users/views:** риск регрессии auth при любой ошибке ручного merge — применять только полный isort-diff, без «частичного» ручного редактирования вперемешку с логикой.
- Working tree уже грязный Black-wrap’ом vs HEAD — на этапе fix отделять вклад isort от старого Black.

---

## 9. Подтверждения

- Branch/HEAD соответствуют ожидаемым.  
- Код четырёх MEDIUM-файлов **не** изменялся этим релизом.  
- Коммитов / push / pull / fetch / checkout / reset / clean — нет.  
- Production / платежи / 1С APPLY / smoke-drill — не запускались.  
- HIGH_RISK и flake8 **не** начинались.

**Остановка. Ожидание согласования следующего этапа.**
