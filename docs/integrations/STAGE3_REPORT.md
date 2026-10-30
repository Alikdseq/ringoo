# Этап B (фаза B1–B5): заказы Ringo ↔ 1С

**Дата:** 28 октября 2026  
**Статус:** реализовано на стороне сайта с mock-тестами. Реальные POST в 1С не выполнялись.

## Принятые решения

1. `paid=false` → после Сбера `paid=true`, тот же `orderId` и снимок позиций.
2. Серии в `Stock` / `OrderItem`; разные серии — отдельные строки.
3. Самовывоз — `Store.onec_warehouse_id`; доставка — `ONE_C_DEFAULT_WAREHOUSE_ID` (иначе `blocked`).
4. Гости: `SiteRegistration/registrate` → `ClientId` в заказе.
5. Публикация: `/razrab/hs/` (не `/ut11_test/`).
6. Фискализация — вне scope.

## Изменённые / новые файлы (ключевые)

- `backend/integrations/onec/client.py` — SiteOrders, ClientId
- `backend/integrations/onec/orders.py` — sync / cancel / payload / серии
- `backend/integrations/onec/importer.py` — остатки по seriesId
- `backend/integrations/onec/registration.py` — ClientId
- `backend/apps/orders/models.py` + `migrations/0007_*`
- `backend/apps/stores/models.py` + `migrations/0006_*`
- `backend/apps/orders/tasks.py`, `views.py`, `services.py`, `admin.py`
- `backend/apps/payments/services.py` — hook paid→1С
- `backend/config/settings/base.py`, `.env.example`
- `backend/tests/test_onec_orders.py`, правки `test_onec_http.py`
- `docs/integrations/1c-api-contract.md`, `EXTERNAL_REQUESTS_CHECKLIST.md`

## Блокеры до живых испытаний

- Подтвердить хост `ONE_C_API_BASE_URL=…/razrab/hs`
- Получить `ONE_C_DEFAULT_WAREHOUSE_ID`
- Секреты только в env; сменить пароль из старой инструкции
- Не POST без явного разрешения
