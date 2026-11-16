# RELEASE 30 — ISORT MEDIUM FIX 3 PREFLIGHT (`apps/orders/models.py`)

**Дата/время:** 2026-11-16 15:05:17 +03:00  
**Режим:** **READ-ONLY** — файл **не** изменялся  
**Вердикт рекомендации:** **SAFE TO FIX** (только in-function перестановка; после отдельного ACK)

---

## 1. Branch / HEAD

| | Значение |
|---|---|
| Branch | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 |
| Tracked CI (после R29) | **18** |
| Файл в remain | да (`isort_remaining_after_r29.txt`) |

git mutate / isort write / Black / deps / платежи / 1С — **не** выполнялись.

---

## 2. Исходное состояние файла

- Working tree: ` M backend/apps/orders/models.py` vs HEAD.
- Pre-existing незакоммиченные правки (не isort): Black-свёртка `is_cancelled` / `is_fulfilled`; лишний blank после локальных импортов в `_generate_order_number` (уже в WT).
- Top-level импорты уже корректны для isort:

```python
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
```

- Единственный isort failure — **внутри** `_generate_order_number()`.

### Назначение функции

Генерирует уникальный номер `ORD-YYYYMMDD-6hex`. Вызывается из `Order.save()` только если `order_number` пуст (цикл с проверкой uniqueness). Field `default` **не** задан (`NOT_PROVIDED`).

---

## 3. Точный isort diff (только in-function imports)

```diff
 def _generate_order_number():
     """Уникальный номер заказа: ORD-YYYYMMDD-6hex."""
+    import random
+
     from django.utils import timezone
-    import random
 
     date_part = timezone.now().strftime("%Y%m%d")
     suffix = f"{random.randint(0, 0xFFFFFF):06x}"
```

| Тип изменения | Есть? |
|---|---|
| Blank между группами (stdlib ↔ django) | да |
| Перестановка двух локальных import-строк | да |
| Merge imports | нет |
| Перенос на module level | **нет** (isort этого не требует) |
| Изменение алгоритма | нет |

---

## 4. Оценка риска

| Вопрос | Ответ |
|---|---|
| Зависимость от порядка импортов? | **Нет.** `random` и `django.utils.timezone` не зависят друг от друга; оба используются только ниже по функции. |
| Локальная область видимости? | Оба имени остаются локальными bindings; семантика `timezone.now` / `random.randint` не меняется. |
| Достаточно переставить два импорта? | **Да.** Это весь требуемый isort fix. |
| Нужен перенос на module level? | **Нет.** Запрещён задачей и не нужен для зелёного isort. |
| Side effects / signals / AppConfig? | Не затрагиваются: правка только порядка lazy-imports внутри helper. |
| Циклы? | Нет: stdlib + Django utils. |

**Риск:** низкий (косметика порядка isort-секций).  
**Ограничение процесса:** in-function → CONDITIONAL до явного ACK (как R27).

---

## 5. Связанные безопасные проверки (выполнены в preflight)

| Проверка | Результат |
|---|---|
| Прямой вызов `_generate_order_number()` после `django.setup()` (test settings) | **OK** — формат `ORD-\d{8}-[0-9a-f]{6}` |
| pytest `TestOrderListCreateViewAPI::test_post_create_order_with_items` | **PASS** (создаёт заказ → `save` → генерация номера; payment_type=cash, без внешних сервисов) |
| pytest `TestOrderCreateSerializer` | **PASS** (12) |
| Итого targeted | **13 passed** |

Не запускались: платежи YooKassa, 1С, smoke/drill, APPLY.

---

## 6. Рекомендация

**SAFE TO FIX** — при отдельном подтверждении на in-function правку.

### Точный объём возможной правки

Только строки импортов внутри `_generate_order_number()`:

```python
def _generate_order_number():
    """Уникальный номер заказа: ORD-YYYYMMDD-6hex."""
    import random

    from django.utils import timezone

    date_part = timezone.now().strftime("%Y%m%d")
    ...
```

- Не трогать тело генерации, `Order.save`, модели, миграции, signals.
- Не переносить `random`/`timezone` на top-level.
- Сохранить существующие Black-изменения в других местах файла.

### Команды после будущего fix (не запускать до ACK)

```text
cd C:\ringoo\backend
venv\Scripts\python.exe -m isort --check-only apps/orders/models.py
venv\Scripts\python.exe -m isort --check-only --diff .
git diff --check -- backend/apps/orders/models.py
venv\Scripts\python.exe manage.py check --settings=config.settings.test
venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.settings.test
venv\Scripts\python.exe -c "import os,django; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.test'); django.setup(); from apps.orders.models import _generate_order_number, Order; print(_generate_order_number())"
venv\Scripts\python.exe -m pytest apps/orders/tests.py::TestOrderListCreateViewAPI::test_post_create_order_with_items apps/orders/tests.py::TestOrderCreateSerializer --override-ini="addopts=" -q
```

Ожидаемый эффект на inventory: tracked CI **18 → 17**.

---

## 7. Подтверждения

- Код `apps/orders/models.py` **не** изменялся этим релизом.
- Коммитов / push / смены ветки нет.
- Production / платежи / 1С не затрагивались.

**Остановка. Ждать подтверждения на FIX.**  
`apps/orders/tasks.py` и прочие failures — вне scope.
