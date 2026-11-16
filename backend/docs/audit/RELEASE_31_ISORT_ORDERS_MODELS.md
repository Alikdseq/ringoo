# RELEASE 31 — ISORT MEDIUM FIX 3 (`apps/orders/models.py`)

**Дата/время:** 2026-11-16 15:08:02 +03:00  
**Основание:** RELEASE 30 = SAFE TO FIX  
**Вердикт:** **PASS**

---

## 1. Branch / HEAD

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| isort | 7.0.0 | 7.0.0 |

git add / commit / push / pull / fetch / смена ветки / Black / deps / другие файлы / production / платежи / 1С APPLY / smoke — **не** выполнялись.  
`apps/orders/tasks.py` — **не** редактировался (остаётся ` M` от прежних правок).

---

## 2. Inventory

| Метрика | До | После |
|---|---:|---:|
| Полный isort fails | **20** (R29 remain) | **19** |
| Tracked CI | **18** | **17** |
| `apps/orders/models.py` в fails | да | **нет** |

Артефакты: `backend/var/r11/isort_batch_r31_files.txt`, `isort_remaining_after_r31.txt`, `isort_remaining_after_r31_classification.json`.

---

## 3. Точный diff (вклад R31)

Только внутри `_generate_order_number()`:

```diff
 def _generate_order_number():
     """Уникальный номер заказа: ORD-YYYYMMDD-6hex."""
+    import random
+
     from django.utils import timezone
-    import random
 
     date_part = timezone.now().strftime("%Y%m%d")
     suffix = f"{random.randint(0, 0xFFFFFF):06x}"
     return f"ORD-{date_part}-{suffix}"
```

- Перенос на module level — **нет**.
- `Order.save()`, модели, поля, сигналы, миграции — **без изменений**.
- Алгоритм генерации — **без изменений**.

Контроль: surgical replace с проверкой, что весь файл кроме этого блока совпал с pre-patch working tree.

### Сохранность прежних Black/wrap

Vs HEAD по-прежнему видны незакоммиченные свёртки `is_cancelled` / `is_fulfilled` — **сохранены**, не откатывались.

---

## 4. Проверки

| Проверка | Результат |
|---|---|
| isort `--check-only apps/orders/models.py` | **PASS** |
| Полный isort | **19** fails / **17** tracked CI |
| `git diff --check` | **PASS** |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| `_generate_order_number()` формат `ORD-YYYYMMDD-6hex` | **OK** (`ORD-20261116-9db67f`) |
| pytest create order + CreateSerializer | **PASS** (13) |

Побочные эффекты: не наблюдались. Внешние сервисы не вызывались.

---

## 5. Остаток MEDIUM

- `apps/orders/tasks.py` — CONDITIONAL (in-function) — **следующий этап только после ACK**.

Классификация остатка (19): HIGH_RISK=9, MEDIUM=1, DEFERRED=7, HOLD=2.

---

## Вердикт

**PASS** — tracked CI **18 → 17**; isort по `orders/models.py` зелёный; тесты/Django OK; правка только локальных импортов в `_generate_order_number()`.

**Остановка.** `apps/orders/tasks.py` не трогать.  
**Никаких коммитов и push.**
