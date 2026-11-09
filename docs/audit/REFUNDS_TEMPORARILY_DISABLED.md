# Возвраты временно отключены

**Дата:** 2026-11-07
**Статус:** OFF by default (`RETURNS_ENABLED=0`, `NEXT_PUBLIC_RETURNS_ENABLED=0`)

## Бизнес-модель на первом этапе

1. Покупатель оформляет и оплачивает заказ.
2. Магазин ведёт заказ в админке.
3. При необходимости возврата покупатель обращается **напрямую в магазин**.
4. Денежный возврат магазин делает вручную в **личном кабинете ЮKassa**.

Встроенный workflow заявок на возврат в Ringoo **скрыт**, но код и данные сохранены.

## Feature flags

| Слой | Переменная | Включение |
|------|------------|-----------|
| Backend API + Django Admin | `RETURNS_ENABLED` | `1` / `true` / `yes` |
| Next.js витрина + Next Admin | `NEXT_PUBLIC_RETURNS_ENABLED` | `1` / `true` / `yes` |

По умолчанию (пусто / `0`) функциональность **выключена**.
Флаги зеркалят паттерн `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED`.

Для восстановления нужно выставить **оба** флага и пересобрать frontend (NEXT_PUBLIC_* инлайнятся при build).

## Что скрыто в UI

### Next Admin

- Пункт меню «Возвраты» (`AdminLayout`) не рендерится при выкл. флаге.
- Страницы `/admin/returns` и `/admin/returns/[id]` отвечают `404` (`notFound()`).

### Витрина / ЛК

- `/profile/returns` → `404`.
- Кнопок «Возврат» / «Запросить возврат» на карточке заказа и в профиле **не было** (страница списка существовала, но не была подключена в навигацию профиля).
- История заказов и статусы оплаты **сохранены**.

### Django Admin

- `ReturnRequest` регистрируется **только** при `RETURNS_ENABLED=1` (`apps/returns/admin.py`).
- При выкл. флаге раздел отсутствует в навигации; таблицы БД не трогаются.

### Юридические тексты

- Блоки офферты / футера про гарантию и возврат по ЗоЗПП **оставлены** (офлайн-процесс через магазин).

## Какие API отключены

При `RETURNS_ENABLED=0` все ниже отвечают **HTTP 403**:

```json
{
  "detail": "Функциональность возвратов временно отключена. Обратитесь в магазин для решения вопроса о возврате.",
  "code": "returns_temporarily_disabled"
}
```

Customer:

- `GET /api/v1/returns/`
- `POST /api/v1/returns/create/`
- `GET /api/v1/returns/<uuid>/`

Admin API:

- `GET /api/v1/admin/returns/`
- `GET /api/v1/admin/returns/<uuid>/`
- `POST /api/v1/admin/returns/<uuid>/transition/`
- `POST /api/v1/admin/returns/<uuid>/refund/`
- `POST /api/v1/admin/returns/<uuid>/inspect/`

URL-маршруты **не удалены** — только gate в views.

## Что сохранено в backend

- App `apps.returns` в `INSTALLED_APPS`
- Модели: `ReturnRequest`, `ReturnItem`, `ReturnEvent`, `MoneyRefund`
- Миграции (`0001_returns_and_color_mapping` и связанные)
- Сервисы: `create_return_request`, `transition_return`, `initiate_money_refund`, `inspect_and_maybe_restock`
- Интеграция ЮKassa refund в сервисах (не вызывается с витрины при флаге OFF)
- Складской restock-путь через returns services
- Unit-тесты сервисного слоя (без HTTP) продолжают работать
- HTTP-тесты API используют `@override_settings(RETURNS_ENABLED=True)`

**Не затронуто:** создание/оплата заказов, статусы платежей, отмена заказа ≠ автовозврат денег, обычные YooKassa payment flows.

## Как включить снова

1. Backend / compose:
   ```bash
   RETURNS_ENABLED=1
   ```
2. Frontend build args / env:
   ```bash
   NEXT_PUBLIC_RETURNS_ENABLED=1
   ```
3. Пересобрать frontend image / `.next` (иначе UI-флаг останется выключенным).
4. Перезапустить `web` (подхватит `RETURNS_ENABLED`).
5. Проверить:
   - меню Admin → «Возвраты»;
   - `POST /api/v1/returns/create/` → 201 при валидных данных;
   - Django Admin → раздел Return requests.

Отключить снова: вернуть оба флага в `0` и пересобрать frontend.

## Изменённые файлы (этап отключения)

- `backend/config/settings/base.py` — `RETURNS_ENABLED`
- `backend/apps/returns/flags.py` — helper
- `backend/apps/returns/views.py` — API gate
- `backend/apps/returns/admin.py` — условная регистрация
- `backend/apps/returns/tests.py` — disabled + enabled HTTP tests
- `frontend/src/lib/features/returns.ts` (+ test)
- `frontend/src/components/admin/AdminLayout.tsx`
- `frontend/src/app/admin/returns/**`
- `frontend/src/app/profile/returns/page.tsx`
- `docker-compose.yml`, `docker-compose.prod.yml`
- `frontend/Dockerfile`
- `.env.example`, `backend/.env.example`, `.env.production.example`
- этот документ
