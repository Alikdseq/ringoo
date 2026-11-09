# Ringoo — реструктуризация админ-панели и подготовка к 1С

**Дата:** 2026-11-07
**Режим:** безопасные изменения без commit/push, без live POST в 1С, без destructive migrations.
**Критерий:** сайт и Next Admin читают **одни и те же** данные Ringoo DB; 1С наполняет БД через уже существующий импорт/HTTP-слой.

---

## 1. Исходное состояние (аудит)

### Навигация Next Admin (было)

Заказы, Товары, **Импорт XLSX**, Категории, Остатки, Пользователи, Контент, Магазины, Менеджеры, Акции, CRM, Аналитика, Возвраты (флаг), Резервное копирование.

### 1С (уже в коде)

Пакет `backend/integrations/onec/`:

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `CatalogFolders/folders` | Категории |
| GET | `CatalogProducts/products` | Товары, цены, остатки в XML |
| POST | `SiteRegistration/registrate` | Контрагент |
| POST | `SiteOrders/orders` | Заказ |
| POST | `SiteOrders/orders/cancel` | Отмена |

Каталог синхронизируется CLI `import_onec_catalog` (не на каждом запросе покупателя).
Beat **не** крутит периодический catalog sync.
`ONE_C_SYNC_PARTNER_ON_REGISTER` был в settings, **не был** подключён к signup.

Админ API ранее **не отдавал** `onec_code` / series / partner status в списках товаров/категорий/остатков/пользователей → UI и сайт были «рассинхронизированы» по видимости 1С-полей.

### CRM vs Заказы

CRM = только `MissingProductRequest` («не нашли товар» + футер). **Не дублирует заказы.**
**Решение: Scenario B — оставить раздел CRM.**

### Промокоды / бонусы / export

- Checkout: промо-поля UI не было; был placeholder-текст.
- `POST /promocodes/validate/` существовал отдельно от order create.
- `BONUS_ENABLED` уже OFF по умолчанию.
- Кнопка «Скачать копию моих данных» была в профиле.

### Геолокация

- Home/Stores: GPS + Haversine.
- Checkout `StoreSelector`: сортировка «по расстоянию» шла от **центроида магазинов**, не от GPS пользователя.

---

## 2–4. Что изменено в админке / что скрыто / что сохранено

| Раздел | Итог |
|--------|------|
| Заказы | Без изменений логики |
| CRM | Оставлен (Scenario B) |
| Товары | Колонка/поля `onec_code`, `updated_at` в API |
| Категории | Дерево + код 1С; create/delete UI убраны; API create/delete 403 |
| Остатки | API отдаёт series / warehouse / product onec_code |
| Пользователи | Статус синхронизации контрагента 1С |
| Акции | Оставлены; вкладка «Промокоды» скрыта (флаг OFF) |
| Аналитика / Контент / Магазины / Менеджеры | Без ломки |
| Импорт XLSX | Скрыт из меню; страница 404; API 403 |
| Возвраты | Скрыты (флаг OFF) |
| Резервное копирование | Скрыто из меню; страница+API+Celery сохранены (superuser URL) |

Feature flags (default OFF):
`RETURNS_ENABLED`, `PRODUCT_XLSX_IMPORT_ENABLED`, `CATEGORY_MANUAL_MUTATIONS_ENABLED`, `PROMOCODES_ENABLED`,
`NEXT_PUBLIC_RETURNS_ENABLED`, `NEXT_PUBLIC_XLSX_IMPORT_ENABLED`, `NEXT_PUBLIC_BACKUP_NAV_ENABLED`,
`NEXT_PUBLIC_PROMOCODES_ENABLED`, `NEXT_PUBLIC_LOYALTY_UI_ENABLED`, `NEXT_PUBLIC_DATA_EXPORT_UI_ENABLED`.

---

## 5. XLSX

- UI и Admin API импорта отключены флагом.
- Код `bulk_import` / template **сохранён**.
- Источник каталога: 1С → `import_onec_catalog` → Ringoo DB → витрина и админка.

---

## 6–8. Категории / товары / остатки

**Архитектура:** покупатель и админ читают Ringoo DB (не 1С на каждый pageview).

**Сделано сейчас (подготовка, без live apply):**

- RO-поля 1С в Admin API + отображение в списках.
- Ручные мутации иерархии категорий запрещены.
- Локальные SEO/описание/is_active остаются редактируемыми.

**Ещё нужно до запуска на сервере (вне этого безопасного прохода):**

1. Согласовать расписание `import_onec_catalog --from-api` (Celery Beat) и политику резервов с владельцем 1С.
2. Журнал синхронизации (модель SyncLog) — **не добавлен** в этом проходе (избежали лишней миграции без контракта).
3. UI-кнопка «Запустить синхронизацию» + предупреждение о возрасте данных.
4. Color-mapping FE на готовый API `/admin/products/color-mappings/`.
5. Не угадывать GUID характеристик — только matched `onec_code`.

Остатки: `quantity` / `reserved_quantity` / `available_quantity` уже разделены в модели Stock; импорт 1С идёт через `apply_onec_stock_upsert`. Двойное списание в 1С без согласования **не делалось**.

---

## 9–10. Контрагенты 1С

**Реализовано:**

- После `RegisterView` вызывается `enqueue_partner_sync_after_register` (never fails signup).
- Celery task `sync_user_partner_to_onec_task` → существующий `register_user_in_onec` (**только** если `ONE_C_API_ENABLED` и `ONE_C_SYNC_PARTNER_ON_REGISTER`).
- Админ видит `onec_partner_*` в списке и карточке пользователя.

**Не делалось:** реальные POST на рабочую 1С (флаги по умолчанию OFF).

**Нужно от специалиста 1С:** подтвердить идемпотентность `SiteRegistration/registrate` при повторном телефоне; метод поиска существующего контрагента (сейчас только create-path).

---

## 11. CRM

**Оставить.** Самостоятельные лиды ≠ заказы. Модели/данные не удалялись.

---

## 12–14. Промокоды / лояльность / профиль

- Checkout: убран текст про промокоды; поля ввода не было.
- `PROMOCODES_ENABLED=0` → validate API 403.
- Акции (marketing) сохранены.
- UI бонусов убран из профиля и order-status; backend bonus уже OFF.
- Кнопка «Скачать копию моих данных» убрана из UI; endpoint `GET /auth/me/export/` сохранён.

---

## 15–16. Геолокация

- `StoreSelector`: при «Ближайшие ко мне» запрашивает GPS (один раз на переключение), Haversine от пользователя, показ км; при отказе — ручной выбор.
- На **HTTPS-домене** Ringoo геолокация браузера должна работать при разрешении пользователя.
- Нужны корректные `Store.latitude/longitude`.
- CSP Yandex Maps / ключ — как раньше; CSP не отключался.

---

## 17. Изменённые файлы (основные)

**Backend:** `config/settings/base.py`, `admin_api/views/{products,stock,users}.py`, `promotions/views.py`, `users/{views,tasks}.py`, `.env.example`.

**Frontend:** `AdminLayout.tsx`, `lib/features/{admin-ui,storefront,returns}.ts`, admin pages (categories, products, import, users, promotions), `StoreSelector.tsx`, `ProfileContent.tsx`, `checkout/page.tsx`, `order-status`, types/services.

**Docs:** этот отчёт; ранее `REFUNDS_TEMPORARILY_DISABLED.md`.

---

## 18–19. Тесты

Выполнено / ожидается:

| Проверка | Результат |
|----------|-----------|
| Ранее: `apps.returns.tests` (test settings) | 5/5 OK |
| Ранее: vitest returns flag | OK |
| Live POST 1С / apply catalog | **Не запускалось** (намеренно) |
| Полный Next build | Требует пересборки frontend контейнера, чтобы пропали пункты меню из старого `.next` |

Если в UI всё ещё виден «Возвраты»/«Импорт XLSX»/«Backup» — это **закэшированный production build**; нужен rebuild frontend (`rm .next` / recreate container).

---

## 20. Оставшиеся проблемы

1. Нет периодического catalog sync и SyncLog UI.
2. Partner sync не включён в env (нужно явное согласование).
3. Color mapping без admin FE.
4. Ручное редактирование цены товара с `onec_code` ещё возможно (локальный override) — нужна политика «1С-поля RO» на PATCH title/sku/price при наличии onec_code.
5. Согласование резервов сайт↔1С с владельцем склада.

---

## 21. До запуска на сервере

1. HTTPS + корректные координаты магазинов.
2. Включить `ONE_C_API_ENABLED` только на согласованном контуре.
3. Прогнать dry-run `import_onec_catalog --from-api`, затем apply.
4. Beat/cron каталога + отображение `last_success_at`.
5. Решение по резервам с 1С.
6. Тест регистрации + partner sync на **тестовой** базе 1С.
7. Регрессия: заказ → ЮKassa → статус (не трогать).
8. Rebuild frontend с новыми `NEXT_PUBLIC_*`.

---

## Итоговая таблица

| Функциональность | Статус | Комментарий |
|---|---|---|
| Категории из 1С | Подготовлено | Импортёр+API RO; ручные create/delete OFF; live sync schedule TBD |
| Товары из 1С | Подготовлено | Поля `onec_*` в админке; apply catalog — CLI |
| Остатки из 1С | Подготовлено | Series/warehouse в API; политика резервов — согласовать |
| Контрагенты в 1С | Каркас готов | Async task; HTTP только при флагах; live POST не выполнялся |
| Заказы | Без регрессии в этом проходе | Не меняли платёжный поток |
| Платежи | Не трогались | ЮKassa сохранена |
| CRM | Оставлен | Scenario B |
| Геолокация | Исправлено в checkout | GPS+Haversine; HTTPS required |
| Административная панель | Упрощена | XLSX/returns/backup/promo tab скрыты |
| Промокоды checkout | Отключены | Акции сохранены |
| Лояльность UI | Скрыта | BONUS_ENABLED уже false |
| Export данных UI | Скрыт | Endpoint сохранён |
| Backup backend | Работает | Только вне меню |

**Не писать «готово» для live 1С-контура:** каталог/остатки/контрагенты требуют согласованного тестового прогона с владельцем 1С.
