# RELEASE 2.1 — Контрольная сверка манифеста перед Git-коммитами

**Дата:** 2026-11-14  
**Режим:** READ-ONLY  
**Проект:** `C:\ringoo`  
**Основание:** `docs/audit/RELEASE_2_COMMIT_MANIFEST.md`  
**Git write / code edit / migrate / APPLY / benchmark run:** не выполнялись  

---

## 1. Git-состояние (свежее)

| Поле | Значение |
|---|---|
| Branch | `main` |
| HEAD | `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8` |
| Modified (`M`) | **76** |
| Untracked (`??`) | **70** (до записи этого отчёта) |
| Status lines | **146** |
| Deleted / Renamed / Conflicts | **0 / 0 / нет** |

После появления этого файла: `?? docs/audit/RELEASE_2_1_FINAL_VALIDATION.md` — **ожидаемо**, не ошибка покрытия манифеста RELEASE 2.

`backend/var/` в status **не** входит (gitignored) — корректно.

---

## 2. Машинная сверка A ↔ B

**A** = пути из `git status --short` (146).  
**B** = Commit 1–9 (139) ∪ Exclude-in-status (7) = **146**.

| Проверка | Результат |
|---|---|
| A − B (пропуски в манифесте) | **∅** |
| B − A (лишние в манифесте) | **∅** |
| Дубликаты между коммитами | **нет** |
| Дубликаты commit ∩ Exclude | **нет** |
| Пути в ≥2 коммитах | **нет** |
| Несуществующие пути на диске | **нет** |
| Счётчики C1…C9 vs таблицы | **42 / 12 / 19 / 9 / 11 / 15 / 5 / 23 / 3** — совпадают |

**Вердикт покрытия:** каждый текущий M/?? путь имеет **ровно одно** назначение (коммит или exclude).

### Ожидаемая дельта после этого отчёта

| Path | Назначение |
|---|---|
| `docs/audit/RELEASE_2_1_FINAL_VALIDATION.md` | **Не** в RELEASE 2. Рекомендация: добавить в **Commit 8** при исполнении (документация), либо оставить untracked до ACK. |

---

## 3. Зависимости Commit 1 ↔ Commit 2

### Изученные файлы

- `backend/integrations/onec/orders.py` → **Commit 1**
- `backend/apps/orders/services/transitions.py` → **Commit 2**
- `backend/apps/orders/services/__init__.py` → **Commit 2**
- `backend/apps/admin_api/views/orders.py` → **Commit 2**

### Ключевой контракт

| Состояние | Сигнатура |
|---|---|
| **HEAD** | `release_order_item_reservations(order)` |
| **Working (C1)** | `release_order_item_reservations(order, *, reason: str = "order_release")` |
| **Working (C2)** | вызывает `release_order_item_reservations(locked, reason=…)` из `transitions.py` и `cancel_order_and_release_stock` |

`admin_api/views/orders.py` (C2): алиасы status / CharField — **не** импортирует `onec.orders`.

### Ответы

1. **Может ли Commit 1 работать на HEAD без Commit 2?**  
   **Да.** Изменения в `orders.py` (series/blank reserve + `reason` с default) обратно совместимы с HEAD-вызовами `release_order_item_reservations(order)`. C1 не требует символов из C2.

2. **Какие символы отсутствуют, если нет?**  
   N/A для C1-alone.  
   **Обратно:** C2 **без** C1 сломается: `TypeError: … unexpected keyword argument 'reason'` на HEAD-сигнатуре.

3. **Безопасно ли создать оба локально подряд без теста/push между ними?**  
   **Да**, при порядке **1 → 2**. Промежуточный HEAD+C1 валиден; C1+C2 валиден. Push только после полного локального набора (см. §6).

4. **Менять порядок / объединять?**  
   **Нет.** Порядок 1→2 обязателен (C2 зависит от C1). Объединение не требуется для безопасности локальных коммитов.

---

## 4. Безопасность benchmark scripts (Commit 9)

Все три: `DJANGO_SETTINGS_MODULE=config.settings.test` → SQLite `:memory:` + `setup_databases` / `teardown_databases`.  
Прямого чтения `.env` / production settings / реальной 1С **нет**.

| Script | Prod / real DB | Stock mutate | APPLY catalog | `apply_onec_stock_*` | Clear tables | Repo OK? | Re-run OK? | README warn? | Commit 9? |
|---|---|---|---|---|---|---|---|---|---|
| `b8_018_load_benchmark.py` | Нет (test DB) | Да, **только test DB** | plan: DRY_RUN; batch upsert на test DB | Да (`apply_onec_stock_upserts_batch`) | teardown test DB | **Да** | Да, если не переопределять settings | **Да** | **Да** |
| `b8_018_rerun_dryrun.py` | Нет | Seed Product на test DB; stock count check; DRY_RUN | Нет APPLY | Нет | teardown | **Да** | Да (нужны fixtures в `var/`) | **Да** | **Да** |
| `b8_018_zero_smoke.py` | Нет *по умолчанию* | **Да** (create Stock + APPLY) | **`ImportMode.APPLY` + `apply_catalog_import`** | косвенно через apply | teardown | Да как код | Только на test settings; опасен при override | **Да (обязательно)** | **Нет без отдельного ACK** |

### Рекомендация по Commit 9

- Включать по умолчанию: **`load_benchmark.py` + `rerun_dryrun.py`** (2 файла).  
- **`zero_smoke.py` — HOLD** до вашего подтверждения (потенциально изменяет данные через APPLY, пусть и на ephemeral test DB).  
- В README / docstring уже есть предупреждения у load_benchmark; для zero_smoke стоит явное «TEST SETTINGS ONLY / не на prod».

Скрипты **не запускались** в этом этапе.

---

## 5. Commit 8 — документация

Все **23** пути существуют, непусты (от ~4.9 KB до ~37 KB).

| Группа | Статус |
|---|---|
| `docs/API.md` | OK (есть trailing whitespace 257–259 — не чинилось) |
| BLOCK 2–8 | OK, 7 файлов |
| Fix Pack A–L | OK, 12 файлов |
| RELEASE 1 / RELEASE 2 | OK |
| `RINGOO_ONEC_FULL_TECHNICAL_AUDIT.md` | OK |
| Коммерческие `.docx` | **не** в Commit 8 (Exclude) — корректно |
| Дубликаты отчётов | Не обнаружены (уникальные имена) |
| Пустые / temp | Нет |
| Секреты (выборочный regex: private key / sk_live / AKIA / postgres URL) | **0 hits** на ключевых doc |

**Добавить при исполнении:** `RELEASE_2_1_FINAL_VALIDATION.md` → Commit 8 (итог станет 24 doc-файла).

---

## 6. Порядок коммитов (подтверждение)

Локальная последовательность **подтверждена** (единый push после всех коммитов):

```
1 OneC / stock / warehouses (+ stores.0008, stores.0009)
2 FSM v2                         ← требует C1 (reason=)
3 Checkout / guest / idempotency ← BE+FE вместе до push
4 Auth refresh
5 AdminGuard                     ← после 4
6 Storefront UI / responsive
7 SEO
8 Documentation                  ← + RELEASE_2_1; whitespace API.md по ACK
9 Optional tooling               ← 2 файла; zero_smoke по ACK
```

**Почему не менять:**  
- C2 жёстко зависит от C1.  
- C3 держит связанные BE/FE commerce-файлы в одном коммите — промежуточный push C3-half невозможен по манифесту.  
- C5 опирается на cookie/staff из C4.  
- При **одном push после 1–8/9** несовместимого remote-состояния не возникает.

Параллельность локально допустима только для независимых веток; для одного `main` working tree — строго 1→9.

---

## 7. Корректировки манифеста (без правок файлов сейчас)

| # | Предложение | Обязательность |
|---|---|---|
| 1 | Добавить `RELEASE_2_1_FINAL_VALIDATION.md` в Commit 8 | Рекомендуется |
| 2 | Commit 9: исключить `b8_018_zero_smoke.py` до ACK | По правилу RELEASE 2.1 |
| 3 | Перед Commit 8: trim trailing whitespace в `docs/API.md` 257–259 | Low, отдельно |
| 4 | Порядок 1–8 не менять; C1+C2 не объединять | Подтверждено |

---

## 8. Блокеры и риски

| Item | Level | Notes |
|---|---|---|
| Ваш ACK манифеста + этой сверки | **Blocker** к `git add`/`commit` | |
| C2 без C1 | High если нарушить порядок | TypeError `reason` |
| stores.0008 на deploy | High | slug mapping / tech-sklad |
| Commit 3 commerce BE/FE | High | не пушить частично |
| `zero_smoke` в C9 | Medium | HOLD без ACK |
| API.md whitespace | Low | pre-commit `--check` |
| Полный test suite после Fix L | Medium | желателен перед push |
| Промежуточный push | **Запрещён по плану** | только после полного локального набора |

**Блокеров к локальным коммитам после вашего подтверждения: нет** (с учётом HOLD на `zero_smoke` и добавления RELEASE 2.1 в C8).

---

## 9. Итоговый вердикт

| Критерий | Статус |
|---|---|
| Покрытие Git status манифестом | **PASS** (146/146) |
| Дубликаты / пропуски | **PASS** |
| Счётчики коммитов | **PASS** |
| C1 на HEAD без C2 | **PASS** |
| C1→C2 локально подряд | **PASS** |
| Порядок коммитов | **CONFIRMED** |
| Commit 8 docs | **PASS** (+ добавить этот отчёт) |
| Commit 9 scripts | **PASS с оговоркой** (hold `zero_smoke`) |
| Готовность к локальным коммитам | **YES после ACK** |

---

## Остановка

`git add` / `commit` / `push` / migrate / APPLY / запуск benchmark — **не выполнялись**.  
Ожидается ваше подтверждение (включая решение по `zero_smoke` и включению этого отчёта в Commit 8).
