# Checkout HTTP 500 — диагностический отчёт

**Дата:** 2026-11-07
**Проект:** `C:\ringoo`
**Commit/push:** не выполнялись

---

## 1. Точная первопричина HTTP 500

**`django.db.utils.ProgrammingError: relation "stores_stock_movement" does not exist`**

При `POST /api/v1/orders/` резервирование остатка вызывает `stock_ops.reserve_at_store` → запись в `StockMovement`. Таблица `stores_stock_movement` в локальной PostgreSQL отсутствовала: миграция `stores.0007_stockmovement` не была применена к рабочей БД Docker.

### Цепочка

1. `apps/orders/views.py` → `OrderListCreateView.post` (~строка 276)
2. `integrations/onec/orders.py` → `plan_and_reserve_at_store` (~строка 314 / `reserve_at_store`)
3. `apps/stores/stock_ops.py` → `StockMovement.objects.filter(...)` / `record_stock_movement`
4. PostgreSQL: `UndefinedTable: stores_stock_movement`

ЮKassa **не** вызывается на создании заказа. Payment создаётся на `POST /api/v1/orders/{id}/pay/`. Timeout ЮKassa **не** был причиной 500 на `/orders/`.

---

## 2. Файл и строка

| Место | Деталь |
|---|---|
| Логи | `POST /api/v1/orders/` → 500, traceback с `stores_stock_movement` |
| View | `backend/apps/orders/views.py` ~276 (`plan_and_reserve_at_store`) |
| Reserve | `backend/integrations/onec/orders.py` ~314 |
| Ledger | `backend/apps/stores/stock_ops.py` (чтение/запись `StockMovement`) |
| Миграция | `backend/apps/stores/migrations/0007_stockmovement.py` |

---

## 3. Внесённые изменения

1. **БД:** применена безопасная миграция `stores.0007_stockmovement` (CreateModel, без удаления данных). Таблица создана, запись в `django_migrations` есть.
2. **CSP (Яндекс Карты):** в `frontend/next.config.ts` добавлены источники:
   - `https://core-renderer-tiles.maps.yandex.net`
   - `https://*.maps.yandex.net`
   в `script-src`, `connect-src`, `img-src` (без `*` глобально и без отключения CSP).
3. Frontend пересобран (`next build` + `next start`) для применения CSP-заголовков.

---

## 4. Как теперь проходит создание заказа

**Фактический тест (DRF, авторизованный пользователь):**

| Сценарий | Результат |
|---|---|
| `payment_type=cash`, pickup, товар с цветом | **HTTP 201** `ORD-20261107-9f101e` |
| `StockMovement` | **+1** операция `reserve`, `success=True`, source `plan_and_reserve_at_store` |
| `payment_type=online` | **HTTP 201** `ORD-20261107-432783`, статус `new`, `checkout_cart_id` сохранён, Payment ещё нет (создаётся на `/pay/`) |

Поток online после фикса:

Корзина → `POST /orders/` (201 + резерв) → `POST /orders/{id}/pay/` → ЮKassa `confirmation_url` → redirect.

---

## 5. Переход на ЮKassa

| Проверка | Статус |
|---|---|
| Создание заказа online без падения 500 | **VERIFIED** |
| Архитектура: pay отдельным endpoint, заказ не откатывается при сбое ЮKassa | **VERIFIED** (код + 201 без Payment) |
| Получение `confirmation_url` через живой API | **BLOCKED** — TLS handshake timeout до `api.yookassa.ru` с host и Docker |
| Обработка сетевой ошибки pay | **IMPLEMENTED** — `yookassa_unreachable` / `yookassa_create_failed` → HTTP 502; UI ведёт на `/payment/fail`, корзина online сохраняется |

Тестовый режим в `.env`: `YOOKASSA_TEST_MODE=1`, shop `1518584`, secret `test_…` — без вывода секрета.

---

## 6. Wishlist 401

| Факт | Статус |
|---|---|
| API `/api/v1/wishlist/` требует `IsAuthenticated` | **VERIFIED** |
| `AppShell` вызывает wishlist только при `enabled: isAuthenticated` | **VERIFIED** |
| 401 для гостя | **ожидаемо**, авторизация не отключалась |
| 401 у «авторизованного» | чаще истёкший JWT / гонка refresh; не первопричина checkout 500 |

---

## 7. CSP / Yandex Maps

| Проверка | Статус |
|---|---|
| До фиксa: `core-renderer-tiles.maps.yandex.net` нарушал `script-src` | воспроизведено в браузере |
| После rebuild: CSP содержит `core-renderer-tiles` и `*.maps.yandex.net` | **VERIFIED** (`CSP_TILES=yes`, FE 200) |
| CSP целиком не отключался | **VERIFIED** |

Полную визуальную проверку карты на странице stores желательно повторить в браузере (кэш).

---

## 8. Результаты тестов

| Набор | Результат |
|---|---|
| `apps.orders` + `apps.stores` | **45 passed** |
| `tests.test_yookassa_payments` | **16 passed** |
| Vitest checkout/orders | **12 passed** (5 files) |
| `tsc --noEmit` | **exit 0** |
| Фактический `POST /orders/` cash + online | **201 VERIFIED** |
| Live ЮKassa pay redirect | **BLOCKED** (сеть/TLS) |
| full `next build` вне Docker | не требовался отдельно — build выполнен в контейнере frontend |

---

## 9. Что осталось / ограничения

1. **TLS к `api.yookassa.ru`** — TCP есть, handshake timeout → нельзя завершить redirect на оплату и test refunds с этой машины.
2. Celery healthcheck помечает worker/beat как unhealthy при живых задачах (не блокирует checkout).
3. Не применялись destructive migrate/down -v; commit/push не делались.

---

## Итог

Checkout 500 **исправлен**: отсутствовала таблица журнала склада после внедрения Block 4 `StockMovement`. После миграции заказы создаются (cash и online). Переход на ЮKassa готов кодом, но **заблокирован сетью** до восстановления TLS. Wishlist 401 для гостя ожидаем. CSP для тайлов Яндекс Карт расширен минимально необходимыми доменами.
