# FIX-PACK H — B8-015: синхронизация документации API

**Дата:** 2026-11-14  
**Среда:** локально `C:\ringoo`  
**Git branch / HEAD до работ:** `main` / `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8`  
**Production / VPS / 1С / платежи:** не затрагивались  
**Runtime (Python/TS), модели, миграции, `.env`:** не менялись  
**Коммит / push:** не создавались  

---

## 1. Что найдено (READ-ONLY)

Источник истины: `backend/config/api_urls.py` → `apps.products.urls` (+ admin_api).  
Frontend (`products.service.ts`) использует `/products/categories/` — совпадает с backend, не с устаревшим `docs/API.md`.

### Таблица endpoint-ов (документация → факт)

| Endpoint в документации (до) | Реальный backend | Frontend | Результат |
|---|---|---|---|
| `GET /api/v1/categories/` | `GET /api/v1/products/categories/` | `/products/categories/` | **Устаревший / несуществующий** (B8-015) |
| `GET /api/v1/categories/{slug}/` | `GET /api/v1/products/categories/{uuid}/` | list + find by slug client-side | **Неверный путь и lookup** (slug ≠ UUID) |
| `GET /api/v1/products/?…` (примеры curl/pagination) | `GET /api/v1/products/products/?…` | `/products/products/` | **Устаревший пример** |
| `?ordering=price` / `-price` | `popular\|price_asc\|price_desc\|rating_desc\|created_at` | те же enum | **Неверные имена параметров** |
| `GET\|POST /api/v1/admin/managers/` | `GET` list; `POST` только `/managers/create/` | admin managers service | **Неверный HTTP-метод на list** |
| Остальные auth/cart/orders/stores/content из списка | Соответствуют `api_urls` includes | используются | **OK** (без правок) |
| `bonus/` | отключён в `api_urls` | — | Документ уже предупреждает — **OK** |

### Отдельно

| Тип | Детали |
|---|---|
| Несуществующие | `/api/v1/categories/`, `/api/v1/categories/{slug}/` |
| Устаревшие примеры | `/api/v1/products/?page=2`, curl без `products/products/` |
| Неверные методы | `POST` на `admin/managers/` (list) |
| Неверные параметры | `ordering=price` / `-price` |
| Lookup | category detail по **UUID**, не slug |

Не документировались заново все остальные существующие API (`wishlist`, `payments`, `promocodes`, `brands`, …) — вне минимального scope B8-015; зафиксированы как пробел документации ниже.

---

## 2. Что исправлено в `docs/API.md`

| Раздел | Изменение |
|---|---|
| Каталог товаров | Categories → `/products/categories/`; detail `{id}` UUID; `is_active` |
| Admin managers | Убран ложный `POST` с list URL |
| Пагинация | `next` → `/products/products/?page=2` |
| Фильтрация товаров | Актуальные query-params + ordering enum |
| Фильтрация заказов | Уточнение status / ordering |
| Примеры curl | Путь списка товаров + публичность каталога |
| Мета | Версия 1.1, дата обновления Fix H |

Backend и frontend **не** менялись.

---

## 3. Проверки

1. Исправленные endpoint-ы сверны с `apps/products/urls.py` и `admin_api/urls.py` — существуют.  
2. HTTP-методы: categories GET; managers list GET; create POST; patch/delete на `{id}`.  
3. Примеры не противоречат `CategorySerializer` / `ProductListView` ordering.  
4. Параметры фильтрации соответствуют docstring/`views.py` каталога.  
5. Ссылок на `/api/v1/categories/` в обновлённом файле нет.  
6. Секреты / `.env` / внутренние credentials не добавлялись.  
7. Приложение не запускалось; внешние системы не вызывались.

---

## 4. Оставшиеся неточности / пробелы (не блокируют B8-015)

1. В `API.md` нет полного перечня: `products/brands/`, `autocomplete/`, `payments/`, `wishlist/`, `promocodes/`, `promotions/`, guest-access orders, returns и т.д.  
2. OpenAPI (`/api/schema/`) — канонический machine-readable контракт; markdown — краткий обзор.  
3. Rate limit числа в markdown могут отличаться от актуальных throttle-классов (не перепроверялись точечно в этом pack).  
4. B8-016+ не трогались.

---

## 5. Подтверждения

| Ограничение | Статус |
|---|---|
| Runtime Python/TS не менялся | Да |
| Миграции не создавались | Да |
| Production не открывался | Да |
| Коммит/push нет | Да |

---

## 6. Изменённые файлы

- `docs/API.md`
- `docs/audit/FIX_PACK_H_API_DOCS_REPORT.md`

---

## 7. Вердикт B8-015

Документированные маршруты категорий и связанные ошибочные примеры приведены к фактическому backend-контракту (`/api/v1/products/categories/`). Runtime неизменен.

**СТОП:** Fix-pack H завершён. B8-016 и следующие этапы не начинались.
