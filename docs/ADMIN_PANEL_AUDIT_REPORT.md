# Аудит административной панели Ringo

**Дата:** 2026-10-30 (обновлено: доработки целостности админки)  
**Объём:** кастомный FE `/admin/*` + Admin API `/api/v1/admin/*` + Django Admin (магазины/1С)  
**Метод:** трассировка UI → service → DRF + `tests/test_admin_integrity.py` (7 цепочек). Браузерный smoke админки **не** запускался на живой БД (host `db` недоступен локально).  
**Связанные документы:** `docs/FULL_FUNCTIONAL_AUDIT_REPORT.md`, `docs/SECURITY_AUDIT_REPORT.md`  
**Промокоды на checkout:** отложены по решению владельца.

**Легенда статуса**

| Статус | Значение |
|--------|----------|
| работает | FE↔BE совпадают, права на месте, нет явной заглушки; подтверждено кодом и/или тестами |
| работает частично | Связка есть, но поля/UX/права/сценарии неполные |
| не работает | Явный разрыв, отсутствующие поля критичны, stub |
| не проверено | Нужен живой браузер / staging / внешняя система |

---

## A. Краткий вывод

Кастомная админка **в целом работоспособна** для каталога, остатков (qty), заказов (статус), пользователей (блок), менеджеров, CRM и промо.  
Критичные пробелы для магазина/1С:

1. ~~Склады `is_warehouse` попадали покупателям~~ — **исправлено в коде** (публичный API + заказ).  
2. `onec_warehouse_id` / `is_warehouse` **не в FE Admin API** — заполнять в **Django Admin** (поля туда **добавлены** в этой сессии).  
3. FE Guard проверяет только `is_staff`, не группы `ringoo_*` → лишние пункты меню → 403.  
4. Оплата/Payment и 1C-sync UI в кастомной админке отсутствуют (осознанно / security).  
5. Content и Analytics **скрыты из сайдбара**, edit статей/новостей неполный.

---

## B. Вход и права

| Функция | FE | BE | Результат | Комментарий |
|---------|----|----|-----------|-------------|
| Логин админа | `/admin/login` → `POST /auth/token/` + `GET /auth/staff-access/` | JWT + StaffAccessView | работает | Не-staff → `/` |
| AdminGuard на все `/admin/*` | `AdminGuard.tsx` | staff-access | работает | Без auth → login |
| Разграничение по группам `ringoo_*` | Нав фильтруется по `staff-access.groups` | Каждый endpoint: IsStaff + группа | работает | Superuser видит всё; staff без групп — предупреждение в сайдбаре |
| Dashboard stats | API есть, UI нет | `GET /admin/dashboard/stats/` | работает частично | `/admin` только redirect на orders |

Группы BE: `ringoo_orders`, `ringoo_catalog`, `ringoo_content`, `ringoo_crm`, `ringoo_reports`, `ringoo_users`, `ringoo_stores` (`admin_api/permissions.py`).

---

## C. Таблица по страницам и функциям

### `/admin/orders` — Заказы

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| Список заказов + фильтры (статус, доставка, оплата, даты, поиск) | работает | `GET /orders/` (staff видит все) |
| Карточка / модалка заказа | работает | `GET /orders/{id}/` |
| Смена статуса заказа | работает | UI показывает только текущий + допустимые next (зеркало BE) |
| CSV export | работает | `GET /admin/orders/export/` |
| Просмотр / смена Payment.paid | не работает | Нет UI/endpoint в admin API (и правильно: paid только через банк) |
| Поля синхронизации 1С на заказе | не работает | Не в публичном/admin serializer UI |
| Живой UI smoke | не проверено | Нужен браузер |

### `/admin/products` — Товары (список)

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| Список + фильтры (категория, бренд, active, поиск) | работает | `GET /admin/products/` |
| Bulk activate/deactivate | работает | `POST …/bulk/set-active/` |
| Bulk цены | работает | `POST …/bulk/update-prices/` |
| CSV export | работает | `GET …/export/` |
| Поля `onec_code` / цвета в списке | работает частично | В модели есть; в list UI нет |

### `/admin/products/new` — Создание товара

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| Создание товара | работает | `POST /admin/products/create/` |
| Загрузка изображений после create | работает | `POST …/images/` |
| Meta / onec / ProductColor | работает частично | Не все поля модели в форме |

### `/admin/products/[id]` — Редактирование товара

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| GET / PATCH / DELETE товара | работает | `…/products/{id}/`, `…/patch/` |
| CRUD изображений | работает | images endpoints |
| CRUD характеристик (specs) | работает | specs endpoints |
| Правка остатка qty по магазинам | работает | `GET/PATCH /admin/stores/stock/` |
| Цвета / onec_* / meta в форме | работает частично | Неполное покрытие модели |
| reserved_quantity UI | работает частично | BE PATCH умеет; FE stock qty в основном |

### `/admin/products/import` — Импорт

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| Скачать шаблон XLSX | работает | wiring `GET …/import/template/` |
| Upload xlsx (+ zip) | работает | wiring `POST …/import/` |
| Runtime на реальном файле | не проверено | Нужен браузер + файл |

### `/admin/categories` — Категории

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| Дерево / список | работает | `GET /admin/products/categories/` |
| Create / update / delete | работает | create + patch/delete |
| `onec_code` категории | работает частично | В модели; в admin serializer/UI нет |
| Image / meta | работает | В форме есть |

### `/admin/stock` — Остатки

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| Drill-down магазин → категория → товары | работает | stores-summary / by-store |
| Редактирование quantity (blur) | работает | `PATCH /admin/stores/stock/{id}/` |
| reserved_quantity / серии 1С | работает частично | Нет UI; данные могут быть в модели |
| Живой UI | не проверено | |

### `/admin/stores` — Магазины (кастомная админка)

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| Список / create / patch / delete | работает | Admin API Store* |
| Изображения магазина | работает | images CRUD |
| `onec_warehouse_id` / name / `is_warehouse` | работает | Добавлено в StoreAdminSerializer + FE форма/таблица (2026-10-30) |
| description / meta в FE форме | работает частично | BE serializer имеет description/meta; FE форма неполная |

### Django Admin — Магазины (`/django-admin/` или `ADMIN_SITE_URL_PATH`)

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| Редактирование `onec_warehouse_id`, `onec_warehouse_name`, `is_warehouse` | работает | Добавлены в `StoreAdmin` fieldsets/list (2026-10-30) |
| Заполнение ID перед 1С sync | работает | Рекомендуемый путь до появления FE admin полей |

### `/admin/managers` — Менеджеры

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| CRUD + фото + привязка к магазину | работает | Полный wiring к ManagerAdmin* |

### `/admin/users`, `/admin/users/[id]` — Пользователи

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| Список / поиск / пагинация | работает | `GET /admin/users/` |
| Блок / разблок (`is_active`) | работает | `PATCH …/patch/` |
| Выдать `is_staff` | работает частично | Кнопка у всех staff; BE только **superuser** (SEC) |
| Группы `ringoo_*` | работает | Чекбоксы на `/admin/users/[id]`; PATCH groups только superuser |
| `onec_partner_*` | не работает | Не в serializer/UI |
| Адреса / профиль readonly | работает | Detail |

### `/admin/content` — Контент (скрыт из навбара)

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| Discoverability (сайдбар) | работает частично | `ADMIN_NAV_HIDDEN_HREFS` — страница есть по прямому URL |
| Articles/News create + delete | работает | create/delete |
| Articles/News edit (PATCH) | работает | GET detail + форма редактирования |
| Reviews approve | работает | PATCH is_approved |
| Page gallery create/delete | работает | gallery endpoints |
| Gallery edit | работает частично | Create/delete; полный edit placement — ограничен |

### `/admin/promotions` — Акции и промокоды

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| Promotions CRUD | работает | adminPromotions.service |
| PromoCodes CRUD | работает | same |
| Image у promotion | работает частично | В BE может быть; FE форма неясна |
| Применение промокода на checkout | не работает | Отдельный публичный `POST /promocodes/validate/` без FE checkout |

### `/admin/crm` — Заявки «нет товара»

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| Список + фильтр статуса | работает | `GET /admin/crm/requests/` |
| Смена статуса | работает | `PATCH …/patch/` |
| Detail страница | работает частично | BE detail есть; UI list-only |

### `/admin/analytics` — Отчёты (скрыт из навбара)

| Функция | Результат | Доказательство / пробел |
|---------|-----------|-------------------------|
| Revenue / orders / top-products | работает | reports API |
| Discoverability | работает | В меню при наличии `ringoo_reports` |
| Export | работает | CSV на вкладках revenue / orders / top |

---

## D. Сводка по статусам (кастомная админка)

| Статус | Кол-во функций (примерно) | Примеры |
|--------|---------------------------|---------|
| работает | ~35 | login, products list/bulk, stock qty, managers, CRM status, users block, promotions CRUD |
| работает частично | ~18 | order status UX, RBAC нав, content edit, is_staff button, analytics hide, product onec/colors |
| не работает | ~8 | warehouse fields в FE admin, payment paid UI, group assignment, checkout promocode, partner 1C user |
| не проверено | ~5 | import runtime, живой smoke всех страниц в браузере |

---

## E. P0 / P1 для админки

| ID | Приоритет | Проблема | Действие |
|----|-----------|----------|----------|
| ADM-01 | P0 ops | Нет `onec_warehouse_id` в FE Admin API | Заполнять в **Django Admin** (поля добавлены). Позже — вынести в StoreAdminSerializer + FE |
| ADM-02 | P0 shop | ~~Склады в публичном списке~~ | **Исправлено:** публичный API и заказ исключают `is_warehouse=True` |
| ADM-03 | P1 | FE не фильтрует нав по `ringoo_*` | Либо отдавать группы в staff-access, либо гейтить пункты меню |
| ADM-04 | P1 | Order status select без фильтра переходов | Показывать только допустимые next-status |
| ADM-05 | P1 | Content/Analytics скрыты; edit неполный | Вернуть в нав или убрать маршруты; доделать PATCH UI |
| ADM-06 | P2 | Нет Payment ops в admin (кроме Django readonly) | Оставить: paid только через банк; мониторинг через management commands |

---

## F. Что сделано в коде (админка + целостность)

1. Публичные магазины / stock: исключён `is_warehouse=True` + тесты.  
2. Django Admin + **кастомная админка** магазинов: `onec_warehouse_*`, `is_warehouse`.  
3. `GET /auth/staff-access/` → `groups` / `is_superuser`; меню фильтруется.  
4. Статусы заказов: только допустимые переходы.  
5. Пользователи: назначение групп `ringoo_*` (superuser).  
6. Контент: редактирование статей/новостей (GET+PATCH).  
7. Аналитика: в меню + CSV export.  
8. Команда `list_onec_warehouses` (+ `--apply mapping.json`).  
9. Цепочки: `tests/test_admin_integrity.py` — **7 passed**.  
10. Пример маппинга: `docs/integrations/onec_warehouse_mapping.example.json`.

**Отложено:** промокоды на checkout; живое заполнение ID складов (нужна доступная БД + реальные UUID из 1С); Vitest/Postgres races; browser smoke.

---

## G. Рекомендуемый порядок дальше (согласован с вашим)

1. ~~Фильтрация `is_warehouse`~~ — сделано в коде.  
2. **Заполнить** `onec_warehouse_id` в Django Admin для всех точек продаж.  
3. Пометить чистые склады `is_warehouse=True`.  
4. Staging + ручной smoke: каталог → корзина → checkout → заказ.  
5. Позже: Admin API поля склада; RBAC нав; Vitest; Postgres concurrency.
