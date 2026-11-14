# FIX-PACK I — B8-016: аудит и синхронизация sitemap

**Дата:** 2026-11-14  
**Среда:** локально `C:\ringoo`  
**Git branch / HEAD до работ:** `main` / `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8`  
**Production / VPS / 1С / платежи / `.env`:** не затрагивались  
**Backend / API / миграции:** не менялись  
**Коммит / push:** не создавались  

---

## 1. Исходные расхождения (до Fix I)

| Источник | Содержимое |
|---|---|
| `sitemap.ts` STATIC | `/`, catalog, promotions, installment, stores, about, order-status, site-map, docs/* — **без** blog/news |
| `site-map/page.tsx` LINKS | `/`, catalog, promotions, stores, **blog, news**, order-status, **cart, checkout**, docs/* — **без** about/installment/site-map |
| Динамика XML | products, categories, stores (API) |
| `robots.ts` | disallow admin/api/cart/checkout/wishlist/orders/profile/login/register — без forgot/reset |

Конфликт: HTML предлагал индексируемые ссылки на cart/checkout; XML не содержал blog/news hubs.

---

## 2. Правила индексации (итог)

### A. Индексировать (статика + динамика XML)

- Главная, каталог, акции, рассрочка, магазины, о нас, блог, новости, карта сайта, order-status, legal docs  
- Динамика: `/products/{slug}`, `/catalog/category/{slug}`, `/stores/{slug}`, `/blog/{slug}`, `/news/{slug}` (из публичного API)

### B. Не индексировать

- `/admin/*`, `/api/*`  
- `/cart`, `/checkout`, `/wishlist`  
- `/login`, `/register`, `/forgot-password`, `/reset-password`  
- `/profile/*`, `/orders/*`, payment return/fail/success  
- `/order-rate`

### C. Требуют осторожности / не в sitemap

| Маршрут | Решение |
|---|---|
| Query-фильтры каталога | Не включать |
| `/staff/{slug}` | Публичные профили есть; **не** добавлены в XML без отдельного безопасного listing-контракта в этом pack (остаточный риск) |
| Пустые категории | API отдаёт slug — URL остаётся валидным page |

---

## 3. Таблица маршрутов (сводка)

| Маршрут | Существует | Публичный | Индексируемый | XML | HTML | Решение |
|---|---|---|---|---|---|---|
| `/` | Да | Да | Да | Да | Да | Index |
| `/catalog` | Да | Да | Да | Да | Да | Index |
| `/catalog/category/{slug}` | Да | Да | Да | Динамика | Нет (hub) | Index XML |
| `/products/{slug}` | Да | Да | Да | Динамика | Нет | Index XML |
| `/promotions` | Да | Да | Да | Да | Да | Index |
| `/installment` | Да | Да | Да | Да | Да | Index |
| `/stores` | Да | Да | Да | Да | Да | Index |
| `/stores/{slug}` | Да | Да | Да | Динамика | Нет | Index XML |
| `/about` | Да | Да | Да | Да | Да | Index |
| `/blog`, `/blog/{slug}` | Да | Да | Да | Hub + динамика | Hub | Index |
| `/news`, `/news/{slug}` | Да | Да | Да | Hub + динамика | Hub | Index |
| `/order-status` | Да | Да | Да (utility) | Да | Да | Index |
| `/site-map` | Да | Да | Да | Да | Да | Index |
| `/docs/*` | Да | Да | Да | Да | Да | Index |
| `/staff/{slug}` | Да | Да | Условно | Нет | Нет | Отложено |
| `/cart`, `/checkout` | Да | Да UX | **Нет** | Нет | **Убраны** | noindex |
| `/wishlist` | Да | Auth UX | Нет | Нет | Нет | noindex |
| `/login`, `/register`, password | Да | Да UX | Нет | Нет | Нет | noindex + robots |
| `/profile/*`, `/orders/*` | Да | Нет | Нет | Нет | Нет | noindex |
| `/admin/*` | Да | Нет | Нет | Нет | Нет | noindex |
| `/order-rate` | Да | Служебный | Нет | Нет | Нет | noindex |

---

## 4. Что исправлено

1. Общий модуль `frontend/src/lib/seo/public-site-routes.ts` — единый статический список.  
2. `sitemap.ts` и `site-map/page.tsx` читают его.  
3. Из HTML убраны cart/checkout; добавлены about, installment, site-map, blog, news (как в политике index).  
4. XML: статика + articles/news из `/content/articles/` и `/content/news/`.  
5. `robots.ts`: disallow forgot/reset-password.

---

## 5. Изменённые файлы

- `frontend/src/lib/seo/public-site-routes.ts` *(new)*  
- `frontend/src/lib/seo/public-site-routes.test.ts` *(new)*  
- `frontend/src/app/sitemap.ts`  
- `frontend/src/app/site-map/page.tsx`  
- `frontend/src/app/robots.ts`  
- `docs/audit/FIX_PACK_I_SITEMAP_REPORT.md`

---

## 6. Проверки

| Check | Result |
|---|---|
| Vitest `public-site-routes.test.ts` | **4 passed** |
| `tsc --noEmit` | OK |
| ESLint изменённых файлов | OK (`--max-warnings 0`) |
| `npm run build` | OK (exit 0) |
| Приватные пути в STATIC list | Отсутствуют (тест) |
| XML/HTML статика | Один источник `PUBLIC_INDEXABLE_STATIC_ROUTES` |

Секреты `.env` не читались. Если API недоступен на build — динамика пустая, статика остаётся (как раньше).

---

## 7. Динамика, не включённая безопасно

- `/staff/{slug}` — нет гарантированного публичного полного crawl-списка в этом pack.  
- Query/filter URL каталога — намеренно исключены.

---

## 8. Остаточные SEO-риски

1. Отсутствие `noindex` metadata на page-level для cart/checkout (robots disallow есть).  
2. Manager pages `/staff/*` вне sitemap.  
3. Canonical/hreflang не менялись.  
4. B8-017–019 не трогались.

---

## 9. Подтверждения

| Ограничение | Статус |
|---|---|
| Backend/API не менялся | Да |
| Production не открывался | Да |
| Коммит/push нет | Да |

**СТОП:** Fix-pack I завершён. B8-017 / B8-018 / B8-019 не начинались.
