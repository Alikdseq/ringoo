# RINGOO — финальная доработка интеграции с 1С и админ-панели

**Дата:** 07.11.2026
**Репозиторий:** `C:\ringoo`
**Базовый отчёт:** `docs/audit/RINGOO_ADMIN_AND_1C_RESTRUCTURING_REPORT.md`
**Статус:** техническая подготовка завершена; **живые тесты с владельцем 1С не проводились** — интеграция не объявляется «полностью готовой».

---

## 1. Исходное состояние

- Импортёр `integrations/onec` + команда `import_onec_catalog` уже существовали.
- Цепочка контрагента: `RegisterView → enqueue_partner_sync_after_register → Celery → register_user_in_onec`.
- Остатки: `quantity` / `reserved_quantity` / `available_quantity`, upsert из 1С.
- Admin API color-mappings уже был, UI не был подключён.
- Ручное изменение цены/остатка для товаров с `onec_code` было возможно.
- Полноценного SyncLog и admin-запуска sync не было; Celery Beat catalog sync не настроен.

## 2. Что обнаружено

| Область | Находка |
|---------|---------|
| PATCH Admin API | Цена/title/sku/category правились без защиты |
| Bulk prices | Менял цены у onec-товаров |
| Stock PATCH | `quantity` правился вручную |
| Django Admin | Только UI, без жёсткого save |
| Sync | Нет журнала запусков / stale-контроля |
| Beat | Каталог не в расписании |
| Color mappings | API есть, Next Admin — нет |
| Резервы | Логика Ringoo рабочая; контракт с 1С не согласован |

## 3. Что исправлено

1. **Защита полей 1С** на Backend (PATCH, bulk prices, stock quantity) + Django Admin save + Next Admin read-only.
2. **OneCCatalogSyncLog** + сервис `catalog_sync` (probe / dry-run / apply + параллельный apply block).
3. **Admin API** `/admin/onec/sync/*` и страница Next Admin `/admin/sync`.
4. **Celery Beat** задача catalog sync — **выключена по умолчанию** (`ONE_C_CATALOG_SYNC_ENABLED=0`).
5. **Color mappings UI** `/admin/color-mappings` (без угадывания GUID).
6. **Тесты** защиты, SyncLog dry-run (fixtures), partner enqueue + идемпотентность (mock).
7. **Документ по резервам** `docs/audit/RINGOO_STOCK_RESERVE_OPTIONS.md`.

## 4. Модели

- Новая: `apps.products.sync_models.OneCCatalogSyncLog` (экспорт через `products.models`).
- Существующие `Product` / `Category` / `ProductColor` / `Stock` не удалялись.

## 5. Миграции

- `backend/apps/products/migrations/0008_onec_catalog_synclog.py` — только SyncLog (+ индексы).
  Применена на локальном Docker (`migrate products 0008… OK`).

## 6. Endpoints

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/api/v1/admin/onec/sync/status/` | Статус, stale, last success |
| GET | `/api/v1/admin/onec/sync/logs/` | История |
| GET | `/api/v1/admin/onec/sync/logs/<uuid>/` | Детали |
| POST | `/api/v1/admin/onec/sync/probe/` | Проверка связи (без записи каталога) |
| POST | `/api/v1/admin/onec/sync/dry-run/` | Dry-run (API или fixtures если API off) |
| POST | `/api/v1/admin/onec/sync/apply/` | Очередь apply (`confirm=true`, только если API enabled) |

Права: staff + группа каталога (`RINGOO_GROUP_CATALOG`). Секреты 1С в ответы не отдаются.

## 7. Read-only поля (при наличии `onec_code`)

**Группа A (1С):** `title`, `sku`, `price`, `old_price`, `category`, `onec_code`, `onec_type`; для stock — `quantity`.

**Группа B (Ringoo):** `description`, `short_description`, `meta_title`, `meta_description`, `slug`, `brand`, `is_active`, `is_featured`, изображения/галерея; для stock — `reserved_quantity`.

Категории с `onec_code`: `title` / `slug` / `parent` / `onec_code` — read-only; ручное create/delete — только при `CATEGORY_MANUAL_MUTATIONS_ENABLED`.

Импортёр при update товара пишет `title`, `onec_code`, `category`, `price` — **не** перезаписывает SEO/описания/фото.

## 8. SyncLog

Поля: `run_id`, тип, источник, статус (`pending|running|success|partial_success|failed`), dry-run, тайминги, счётчики категорий/товаров/остатков, `error_messages` (без секретов), `summary`, инициатор, `celery_task_id`.

- Exception → `failed`.
- Issues + изменения → `partial_success`.
- Успешный **apply** учитывается в `last_success` (неуспех не затирает).
- Параллельный apply блокируется (`has_running_apply`, окно stale running 120 мин).

## 9. Запуск синхронизации

1. Next Admin → «Синхронизация 1С».
2. Probe / Dry Run / Apply (apply с `window.confirm`).
3. Apply → Celery `run_onec_catalog_sync_task` (не в HTTP-потоке).
4. При `ONE_C_API_ENABLED=false`: dry-run по fixtures; apply → 403.

## 10. Celery Beat

- Env: `ONE_C_CATALOG_SYNC_ENABLED`, `ONE_C_CATALOG_SYNC_INTERVAL_SECONDS`, `ONE_C_CATALOG_STALE_HOURS`.
- Задача: `apps.products.tasks.scheduled_onec_catalog_sync_task`.
- По умолчанию **OFF**. Включать только после согласования нагрузки с владельцем 1С.

## 11. Сопоставление цветов

- API: `/admin/products/color-mappings/`.
- UI: `/admin/color-mappings` — ручной ввод подтверждённого кода; без автоугадывания по названию.

## 12. Контрагент

- Регистрация сайта **не падает**, если 1С/Celery недоступны.
- Повторный `register_user_in_onec` при уже сохранённом `onec_partner_id` → skip.
- Таймаут без HTTP-кода → `pending_review` (без слепого повторного POST).
- В 1С уходят только ФИО + телефон (не пароль/JWT/платежи).

## 13. Согласовать с владельцем 1С

1. Поведение `SiteRegistration/registrate` при повторном телефоне.
2. Формат ответа и стабильный GUID контрагента.
3. Нужен ли поиск существующего контрагента.
4. Расписание/лимиты catalog GET (folders/products).
5. GUID характеристик/цветов в выгрузке (без угадывания на сайте).
6. Политика отсутствия SKU во временной выгрузке (сейчас Ringoo не удаляет).

## 14. Резервы

См. `docs/audit/RINGOO_STOCK_RESERVE_OPTIONS.md` (варианты A/B/C). Логика резервирования Ringoo **не менялась**. Остатки в 1С с сайта не пишутся.

## 15. Тесты

| Проверка | Результат |
|----------|-----------|
| `manage.py check` (test settings) | OK |
| `tests.test_onec_field_protection` | OK (3) |
| `tests.test_onec_sync_log` | OK (3) |
| `tests.test_onec_partner_enqueue` | OK (3) |
| Live POST в рабочую 1С | **не выполнялся** |
| Live apply / реальные платежи | **не выполнялись** |

## 16. Сборка Frontend

- Страницы `/admin/sync`, `/admin/color-mappings`, правки карточки товара.
- `npx tsc --noEmit` (Docker frontend): **OK (exit 0)**.
- `npx vitest run src/lib/api/services`: **5 passed**.
- `npm run build` (Docker frontend): **OK (exit 0)**; маршруты `/admin/sync` и `/admin/color-mappings` в сборке присутствуют.

## 17. Известные ограничения

- Нет live-подтверждения контракта 1С.
- Beat catalog sync выключен.
- Apply намеренно заблокирован при выключенном API.
- Идемпотентность контрагента на стороне 1С зависит от их API (поиск не придуман).
- XLSX / returns / backup / promocodes UI остаются скрытыми по принятым ранее решениям.
- ЮKassa / checkout / cart не менялись в рамках hardening.

## 18. Перед AdminVPS

1. Применить миграцию `products.0008_onec_catalog_synclog`.
2. Выставить секреты 1С только в env сервера (не в git / не в `NEXT_PUBLIC_*`).
3. Оставить `ONE_C_API_ENABLED=0` до smoke на согласованном контуре.
4. Сначала probe + dry-run; apply — только после ОКды владельца 1С.
5. `ONE_C_CATALOG_SYNC_ENABLED` включать осознанно с интервалом.
6. `ONE_C_SYNC_PARTNER_ON_REGISTER` — после подтверждения registrate.
7. Rebuild frontend-образа с актуальными feature flags.
8. Smoke: импорт test SKU → витрина/админ цена-остаток → PATCH цены 400 → SEO edit OK → регистрация без 1С → заказ/резерв на тесте → ЮKassa test без live charge.

---

**Итог:** Ringoo готов к безопасной приёмке контракта 1С (защита данных, журнал, dry-run, UI, тесты на mock). Готовность «в бою с 1С» — только после совместных тестов с владельцем 1С.
