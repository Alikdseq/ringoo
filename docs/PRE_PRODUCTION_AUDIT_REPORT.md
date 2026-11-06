# Pre-Production Audit — Ringo (первое публичное размещение без эквайринга)

| Поле | Значение |
|------|----------|
| Дата | 2026-11-02 |
| Ветка | `main` (синхронизирована с `origin/main` на момент аудита) |
| HEAD | `8a0bd5f` — *Document security, 1C, and admin panel audit findings* |
| Режим | **Только аудит.** Исправления, commit, push, deploy **не выполнялись**. |
| База оценки кода | **Закоммиченный HEAD**, если не указано иное. |
| Working tree | ~165 изменённых/untracked путей (в основном frontend UI, `copy-site/`, DOCX, `.cursor/`). **Не входят в remote.** Dirty `checkout/page.tsx` содержит stock-gating, которого **нет в HEAD**. |
| Docker на момент аудита | Compose **не запущен** (`web` down) — живой browser smoke в этой сессии **не выполнялся**. |
| Связанные отчёты | `SECURITY_AUDIT_REPORT.md`, `FULL_FUNCTIONAL_AUDIT_REPORT.md`, `ADMIN_PANEL_AUDIT_REPORT.md`, `SECURITY_OWNER_CHECKLIST.md`, `AUDIT_READINESS_SBER_1C_KASSA.md` |

---

## 1. Общий вердикт

### **READY WITH CONDITIONS**

Сайт **можно** готовить к размещению на **отдельном** сервере для публичного просмотра каталога и демо сценариев **без** живого Сбера / ЮKassa / 1С / кассы — **после** выполнения блокирующих условий ниже.

**Нельзя** считать проект готовым «как есть» к передаче ссылки Сберу/ЮKassa на модерацию: юридический контент и UX оплаты неполны; production-compose не greenfield-ready.

Окончательное решение модерации платёжного сервиса **не гарантируется** этим аудитом.

---

## 2. Сводка

| Метрика | Оценка |
|---------|--------|
| Всего зон проверки (агрегировано) | ~95 |
| Пройдено / приемлемо | ~58 |
| Не пройдено (проблемы) | ~27 |
| Не проверено / частично (нет E2E, Docker down, нет живого HTTPS) | ~10 |
| **Critical** | **4** |
| **High** | **11** |
| **Medium** | **9** |
| **Low / Info** | **остальные** |

Автопроверки (эта сессия):

| Проверка | Результат |
|----------|-----------|
| `npm run type-check` | **PASS** |
| `npm run lint` | **PASS** (0 errors, 106 warnings) |
| Vitest | **FAIL** — 14 files / 10 tests failed (+ jsdom/undici errors); покрытие ненадёжно |
| Backend pytest (orders/stores/users/payment_security/admin_integrity/sber) | **130 passed** |
| `makemigrations --check` (test settings) | **No changes detected** |
| `manage.py check --deploy` (local host) | **Не выполнен** — нет `pythonjsonlogger` в host venv |
| `npm audit --omit=dev` | **5 moderate** (Sentry → glob/minimatch) |
| `pip-audit -r backend/requirements.txt` | **No known vulnerabilities found** |
| Playwright / Cypress E2E | **Отсутствуют** |
| Live HTTP / browser console | **Не проверено** (Docker down) |
| Postgres concurrency tests | **Не запускались** (требуют отдельную test DB) |

---

## 3. Frontend Audit

### 3.1 Архитектура и маршруты

Next.js App Router, ~53 `page.tsx`. Публичные маршруты включают: `/`, `/catalog`, `/catalog/category/[slug]`, `/products/[slug]`, `/cart`, `/checkout`, `/stores`, `/about`, `/blog`, `/news`, `/promotions`, `/installment`, `/wishlist`, auth/profile/orders, payment return/fail, `/order-status`, `/docs/*`, `/site-map`. Admin: `/admin/*` за `AdminGuard`.

Есть `error.tsx`, `not-found.tsx`, `global-error.tsx`, root `loading.tsx`. Segment loading — в основном catalog/product.

API: `lib/api/client.ts` (axios, CSRF/cookies или Bearer). Same-origin `/api/v1` + proxy — нормальный паттерн для prod за одним доменом.

### 3.2 Юридические / информационные страницы

| Страница | Статус |
|----------|--------|
| Политика ПДн `/docs/privacy` | Есть, содержательная |
| Согласие ПДн `/docs/consent` | Есть |
| Cookies `/docs/cookies` | Есть |
| Marketing consent | Есть (в sitemap; в footer docs — слабее) |
| Оферта `/docs/offer` | Есть, **тонкая**; оплата/возврат отсылают к разделу сайта |
| Реквизиты `/docs/requisites` | Структура есть; **ИНН/ОГРН/КПП из env** — иначе плейсхолдеры «укажите NEXT_PUBLIC_ORG_*» |
| Доставка | **Нет** отдельной `/docs/delivery` — footer → `/#delivery-payment` |
| Возврат / гарантия | **Нет** отдельной страницы — тот же якорь |
| Контакты | **Нет** `/contacts` — якорь + блок в реквизитах |

Организация в коде (`seo/constants.ts`): ООО «Рингу», телефон, email, адрес во Владикавказе — **есть**. ИНН/ОГРН **не захардкожены** (корректно), но **обязаны** быть заданы в env до публичной проверки.

### 3.3 Checkout / оплата (без живого эквайринга)

- Offline: cash / card_on_delivery / bank_transfer.
- «Онлайн-оплата» **всегда** в UI; **нет** флага скрытия при `SBER_ECOM_ENABLED=false`.
- При `payment_type=online`: `initiateOrderPayment` → redirect на `form_url`.
- **Critical UX:** если initiate **успешен**, но `form_url` пуст — код **падает в** `/orders/{id}/success` (`checkout/page.tsx` ~176–185).
- При ошибке initiate — `/payment/fail` (приемлемо).

**Dirty tree:** локальный checkout добавляет проверку остатков по магазинам (`getProductStock` / `useQueries`). В **HEAD этого нет**. Деплой HEAD ≠ то, что сейчас в рабочей копии.

### 3.4 UI / mobile / perf (код)

- Responsive header + MobileMenu — выглядят продуманно (код).
- `next/image` преобладает; Metrika pixel — raw `<img>` (ок).
- Тяжёлые 3D/Ringik зависимости — риск веса бандла (Medium).
- CSP допускает `'unsafe-inline'/'unsafe-eval'` в script-src (Medium).
- Живая проверка desktop/tablet/mobile, битых картинок и консоли браузера — **не выполнена** в этой сессии.

### 3.5 Тесты FE

- Vitest unit/component — **нестабильны** (10 failed + environment errors).
- E2E (Playwright/Cypress) — **нет**.

---

## 4. Backend Audit

### 4.1 Запуск и конфигурация

- Django 5.1 + DRF, Celery, Redis, PostgreSQL — архитектура на месте.
- Integrations: Sber (`payments` + `integrations/sber`), 1С (`integrations/onec`), fiscal placeholder.
- Defaults: `SBER_ECOM_ENABLED` / `ONE_C_API_ENABLED` / `ONE_C_ORDER_SYNC_ENABLED` — **выкл**, если env не включает.
- Production: при включённом Sber без callback token — `ImproperlyConfigured` (fail-closed).

### 4.2 Заказы и цены

Подтверждено кодом + тестами ранее/сейчас:

- Цена и total считаются на сервере из каталога.
- Клиентский `delivery_cost`/`total` перезаписываются.
- Магазины с `is_warehouse=True` отфильтровываются для выбора покупателем.
- Order detail — владелец/staff (IDOR mitigations в тестах payment/orders).

### 4.3 Платежи при выключенном Sber

- Register к банку не ходит при disabled.
- `payment_type=online` **всё ещё принимается** API → заказ создаётся, pay fail-closed с безопасным сообщением (**High** для UX/мусорных заказов).

### 4.4 Admin / API

- Admin API + `staff-access` groups — усилены (коммит `67a03ae`).
- Django Admin: OTP **по умолчанию off**, URL default `admin` (**High** ops).
- Bonus admin views — только `IsStaff` без group (Medium).

### 4.5 Ошибки / throttling

- DRF throttling на auth/orders/payments — есть.
- При `DEBUG=False` traceback клиенту не отдаётся (стандарт Django/DRF).
- `/health/` может отдавать текст исключения БД/кэша (Medium).

### 4.6 Автопроверки BE

- 130 релевантных тестов — **pass**.
- Миграции моделей согласованы (`makemigrations --check` — чисто).
- Host `check --deploy` — blocked tooling (`pythonjsonlogger`); нужен запуск **внутри prod-образа**.

---

## 5. Database Audit

| Тема | Статус |
|------|--------|
| Модели + миграции payments / onec / warehouse | Присутствуют (`payments.0001`, `orders.0007`, `stores.0005–0006`, `products.0006`, `users.0005`) |
| Drift models↔migrations | Не обнаружен (`makemigrations --check`) |
| Индексы / FK | Базовые есть (в т.ч. onec_sync_status); полный DBA-review индексов prod — не делался |
| Пустая БД | Каталог/магазины пусты → сайт «пустой»; нужен seed/import каталога **без** записи в боевую 1С или из дампа staging |
| Зависимость от локальных данных разработчика | Высокая для демо: без каталога магазин выглядит незавершённым |
| Destructive migrations | Не запускались |

**Требования к новой staging/prod БД:**

1. Отдельный инстанс Postgres (не общая с локальной/чужой prod).
2. Сильный пароль; **не** публиковать порт наружу.
3. `migrate` при деплое.
4. Seed: категории, товары, остатки по магазинам, `is_warehouse` корректно, контент/магазины.
5. Backup до любых массовых import.
6. Не включать `ONE_C_ORDER_SYNC` до контракта.

---

## 6. Functional Audit

Легенда: **Pass*** = код+тесты; **N/V** = не верифицировано live; **Fail** = дефект/дыра.

| # | Сценарий | Результат | Комментарий |
|---|----------|-----------|-------------|
| 1 | Открытие сайта | N/V | Docker down; ранее после rebuild был HTTP 200 |
| 2 | Каталог | Pass* | API/tests; live N/V |
| 3 | Категории | Pass* | |
| 4 | Карточка товара | Pass* | |
| 5 | Поиск | Pass* / N/V | код есть; live N/V |
| 6–8 | Корзина add/qty/remove | Pass* | BE/FE hooks; Vitest cart flaky |
| 9–10 | Магазин / остатки | Pass* BE; **Gap HEAD FE** | Dirty checkout stock gating ≠ HEAD |
| 11 | Способ получения | Pass* | |
| 12–13 | Данные / валидация | Pass* | |
| 14 | Создание заказа (test) | Pass* | pytest |
| 15 | Результат оформления | **Fail UX online** | empty `form_url` → success; online виден при Sber off |
| — | Онлайн-оплата живая | **Запрещено / не проверялось** | правильно для этапа |
| — | 1С write | **Запрещено / off by default** | |
| — | Касса | Placeholder | не мешает, если не вызывается |

---

## 7. Security Audit

### Critical

| ID | Проблема | Риск |
|----|----------|------|
| SEC-C1 | `production.py`: при `DEBUG=True` пропускаются проверки `SECRET_KEY` / `ALLOWED_HOSTS` | Утечка traceback, Host issues |
| SEC-C2 | `load_dotenv(.env.development)` + compose `env_file` development; `docker-compose.prod.yml` **не** отменяет | Prod-процесс с dev-секретами/CORS |
| SEC-C3 | Dev compose публикует DB/Redis; prod overlay **не** закрывает порты | Компрометация БД/Redis на VPS |
| SEC-C4 | Checkout: online + пустой `form_url` → success | Ложное «успешно оплачено/оформлено» |

### High

| ID | Проблема |
|----|----------|
| SEC-H1 | `docker-compose.prod.yml` неполный: bind-mount backend, Dockerfile.dev, без migrate/collectstatic entrypoint |
| SEC-H2 | `SECURE_PROXY_SSL_HEADER` только для Vercel — за nginx TLS без X-Forwarded-Proto — ломаются cookies/redirect |
| SEC-H3 | CORS/CSRF origins по умолчанию localhost / пусто — нужны явные https-домены |
| SEC-H4 | Django Admin path/OTP по умолчанию слабые |
| SEC-H5 | `payment_type=online` при выключенном Sber |
| SEC-H6 | Нет FE-гейта «Онлайн-оплата» |
| SEC-H7 | Реквизиты без INN/OGRN в env → публичные плейсхолдеры |
| SEC-H8 | Нет E2E на критический путь |
| SEC-H9 | Vitest красный — регрессии UI не ловятся стабильно |

### Medium / Low (выборка)

- Health leak exception text; bonus admin IsStaff-only; Axes proxy count; media serving plan без S3; HSTS preload агрессивен; npm moderate Sentry/glob; CSP unsafe-eval; Ringik weight.

**Секреты в Git:** реальные `.env` не аудитились на содержимое (запрет); в отчёт не включались. Untracked DOCX/integration folders не должны попадать в публичный deploy artifact.

---

## 8. DevOps / Deployment Audit

| Компонент | Готовность |
|-----------|------------|
| Frontend production Dockerfile (standalone) | Есть |
| Frontend Dockerfile.dev + compose volume | Dev-ориентирован; volume `node_modules` уже вызывал 500 (Sentry/`require-in-the-middle`) |
| Backend gunicorn via prod overlay | Частично |
| `docker-compose.prod.yml` | **Недостаточен** для безопасного greenfield |
| `docker-compose.no-host-db-redis-ports.yml` | Есть — **обязан** применяться на сервере |
| Nginx / TLS в репо | Нет готового полного prod reverse-proxy playbook в compose |
| Healthchecks | Есть в compose |
| Restart policies | Стандарт compose |
| Backup/restore | Документировать на уровне ops (owner checklist) |
| Отдельный сервер с нуля | **Да, возможно**, если: отдельный VPS, свои env, закрытые порты DB/Redis, migrate+seed, Sber/1С **off**, HTTPS terminator + proxy headers |

Vercel-пути в коде (ON_VERCEL) — альтернативный хостинг; для «свой сервер» нужен явный nginx/Caddy профиль.

---

## 9. ЮKassa / Сбер Audit (публичная проверка сайта)

### Уже есть в продукте

- Витрина/каталог/карточки/корзина/checkout (offline pay).
- Юр. имя, телефон, email, адрес в константах.
- Политика ПДн, согласие, cookies, оферта, страница реквизитов.
- Согласия в формах (ConsentCheckboxes).

### Нужно от владельца бизнеса (не выдумывать)

1. Реальные **ИНН, ОГРН, КПП** (и р/с при необходимости) → `NEXT_PUBLIC_ORG_*`.
2. Утверждённые тексты: **доставка**, **оплата**, **возврат**, **гарантия** (полные, не один абзац на главной).
3. Подтверждение телефона/email/адреса и режима работы.
4. Решение: показывать ли «Онлайн-оплата» до договора с банком (**рекомендация аудита: скрыть**).
5. Каталог с реальными/согласованными ценами и описаниями (не пустая БД).
6. Соцсети: убрать placeholder Instagram/Telegram или дать реальные URL.

### Риски для модерации

- Плейсхолдеры ИНН на `/docs/requisites`.
- Доставка/возврат только якорем на главную.
- Кнопка онлайн-оплаты, которая не ведёт в банк.
- Сайт без наполненного каталога выглядит как заготовка.

**Вердикт для передачи ссылки банку:** **не готов**, пока не закрыты условия раздела 10 (юридика + UX оплаты + наполнение).

---

## 10. Список блокирующих проблем

| ID | Описание | Где | Почему | Риск | Рекомендация |
|----|----------|-----|--------|------|--------------|
| B1 | Prod compose/env footguns (dev env_file, открытые DB/Redis, DEBUG bypass SECRET_KEY) | `production.py`, `base.py`, `docker-compose*.yml` | Легко поднять «prod» небезопасно | Компрометация / утечки | Отдельный prod env; запрет DEBUG; overlay без publish DB/Redis; не mount `.env.development` |
| B2 | Нет полноценных страниц доставки/возврата/контактов | `Footer.tsx`, нет `/docs/delivery|returns` | Требование витрины для эквайринга/потребителя | Отказ модерации | Отдельные страницы + ссылки в footer |
| B3 | ИНН/ОГРН не заданы → плейсхолдеры | `docs/requisites`, `legal/constants.ts` | Публичный «укажите env» | Отказ модерации / доверие | Заполнить env до публикации |
| B4 | Онлайн-оплата в UI при Sber off + empty `form_url`→success | `checkout/page.tsx` | Ложный успех / сломанный сценарий | Жалобы, модерация | Скрыть online; fail при пустом form_url |
| B5 | HEAD ≠ dirty checkout stock | `checkout/page.tsx` (WT) | Деплой без локальных правок теряет UX остатков | Оверселл | Согласовать и закоммитить отдельно **или** принять риск HEAD |
| B6 | Нет E2E; Vitest красный | frontend tests | Нет страховки критического пути | Регрессии на проде | Минимум smoke E2E + починить Vitest |
| B7 | Пустая/несогласованная prod-БД без seed | ops | Пустой магазин | Модерация/демо fail | Seed каталога + магазины на staging DB |
| B8 | TLS/proxy headers не описаны для non-Vercel | `production.py` | Сломанные secure cookies | Auth/checkout | Nginx + `SECURE_PROXY_SSL_HEADER` + Axes proxy |

---

## 11. План подготовки к размещению (порядок)

1. **Зафиксировать** состав деплоя: только HEAD **или** отдельный PR с нужными FE-правками (checkout stock) — без `copy-site/`, DOCX, `.cursor/`.
2. Подготовить **отдельный VPS** + firewall (80/443 only public).
3. Создать **prod `.env`** (не development): `DEBUG=False`, длинный `SECRET_KEY`, `ALLOWED_HOSTS`, CORS/CSRF https origins, сильные DB/REDIS passwords, `SBER_ECOM_ENABLED=0`, `ONE_C_*=0`, `NEXT_PUBLIC_ORG_INN/OGRN`, `NEXT_PUBLIC_SITE_URL`.
4. Compose: `docker-compose.yml` + `docker-compose.prod.yml` + **`docker-compose.no-host-db-redis-ports.yml`**; убрать bind-mount кода и `.env.development` для web в целевом профиле.
5. Reverse proxy (Caddy/Nginx) → TLS; выставить forwarded proto; HSTS после проверки сертификата.
6. `migrate`, `collectstatic`, создать superuser; сменить `DJANGO_ADMIN_URL`; рассмотреть OTP.
7. Seed каталога/магазинов/остатков (без live 1С POST, если нет разрешения).
8. **Скрыть** онлайн-оплату до договора; offline checkout smoke.
9. Добавить страницы доставка/возврат/контакты; убрать плейсхолдеры реквизитов.
10. Smoke: главная, каталог, PDP, корзина, заказ cash, реквизиты, privacy, mobile.
11. Только после этого — публичная ссылка **на проверку контента** Сберу/ЮKassa (всё ещё **без** боевого эквайринга).
12. Эквайринг/1С/касса — **отдельным** согласованием после одобрения.

---

## 12. Финальное заключение

1. **Можно ли собирать production build?**  
   **Да** (type-check OK; ранее build проходил). Следить за volume/`node_modules` в Docker.

2. **Можно ли развернуть на отдельном сервере?**  
   **Да, с условиями** (B1, B7, B8). Текущий `docker-compose.prod.yml` **сам по себе недостаточен**.

3. **Можно ли подключить домен и HTTPS?**  
   **Да**, стандартным reverse proxy; нужна явная настройка proxy SSL header вне Vercel.

4. **Можно ли открыть сайт публично для проверки ЮKassa/Сбера?**  
   **Пока нет** — сначала B2–B4, B7 и реквизиты. После условий — **да для контентной проверки**, без включения эквайринга.

5. **Обязательные изменения до публикации**  
   Prod env/hardening; закрыть DB/Redis; реквизиты; страницы доставка/возврат; скрыть/починить online pay; seed каталога; smoke на HTTPS.

6. **Какие интеграции оставить отключёнными**  
   Сбер ecom, ЮKassa (ещё нет), 1С API/order sync, онлайн-касса/fiscal, партнёрский sync 1С при регистрации.

7. **Что запрещено до отдельного согласования**  
   Commit/push без разрешения; deploy на существующую prod-БД; `git reset --hard` / clean / restore; реальные платежи; POST в 1С; включение `SBER_ECOM_ALLOW_PRODUCTION` / боевого epay; публикация секретов; destructive migrations на живых данных.

---

## Приложение A. Состояние Git (baseline аудита)

```
Branch: main...origin/main
HEAD:   8a0bd5f
Dirty:  ~165 paths (frontend UI dominant)
Untracked (не для деплоя): .cursor/, copy-site/, integration1CandKassa/, docs/*.docx,
  onec_import_report_dry_run.json, scripts/generate_integration_report_docx.py, Описание работ.txt
```

Последние релевантные коммиты: Sber Phase A → payment security → 1С/warehouse → admin RBAC → audit docs.

## Приложение B. Что не проверялось

- Живой браузер / Lighthouse / CWV на текущем стенде.
- Реальный TLS handshake будущего домена.
- Содержимое локальных `.env` / `.env.development` (секреты).
- Полный npm/pip tree beyond audit CLI.
- Нагрузочное тестирование.
- Ручная модерация ЮKassa/Сбер (вне компетенции кода).

---

*Конец отчёта. Исправления — только после отдельного разрешения.*
