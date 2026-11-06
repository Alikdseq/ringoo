# RINGO — накопительный аудит

Единый файл отчётов по блокам аудита. Предыдущие разделы не удаляются; уточнения добавляются отдельными пометками с номером блока.

---

# БЛОК № 1 — ИНВЕНТАРИЗАЦИЯ И ТЕХНИЧЕСКАЯ КАРТА

**Дата:** 2026-11-05  
**Статус:** завершён (отчёт ранее передан пользователю в чате; полный текст в репозитории до создания этого файла отсутствовал)  
**Источник:** результаты Блока № 1 из сессии аудита (подтверждённые сведения по коду). Ниже — краткая техническая карта **только в пределах ПОДТВЕРЖДЁННЫХ** фактов; детальный развёрнутый отчёт A–O был выдан в Cursor отдельно и сюда не «восстанавливался» целиком по памяти.

## B1. Краткая техническая карта (подтверждено кодом)

| Параметр | Значение |
|---|---|
| Корень | `C:\ringoo` |
| Стек | Django 5.x + DRF, Next.js 16.4.3 / React 19, PostgreSQL 15, Redis 7, Celery/Beat |
| API | `/api/v1/` (`backend/config/api_urls.py`) |
| Apps | users, products, stores, cart, orders, payments, content, promotions, crm, wishlist, bonus (API off), admin_api, audit |
| Integrations | yookassa, sber (gated), onec, fiscal (stub) |
| Платежи | ЮKassa приоритет; Сбер по флагу; `checkout_cart_id` + clear после PAID |
| FE routes | 53 `page.tsx`; proxy в `frontend/src/proxy.ts` (не `middleware.ts`) |
| Git на момент B1 | ветка `main`, HEAD `8a0bd5f`, dirty working tree |

## B1. Пометка о полноте

Полный отчёт Блока № 1 (разделы A–O) был выдан пользователю в чате. В репозитории отдельного файла отчёта не было. В этот накопительный файл внесена краткая карта; при необходимости полный текст B1 можно дописать отдельным согласованным шагом без перезаписи B2.

---

# БЛОК № 2 — КОМПЛЕКСНЫЙ АУДИТ БЕЗОПАСНОСТИ BACKEND И API

**Дата аудита:** 2026-11-05  
**Статус блока:** завершён (статический анализ кода; runtime-эксплойты и обращения к ЮKassa/1С/prod DB не выполнялись)  
**Режим:** READ-ONLY; изменён только этот файл `docs/audit/RINGO_FULL_AUDIT.md`.

## 1. Цель и границы аудита

Цель — выявить реальные и потенциальные уязвимости Backend/API Ringoo (IDOR/BOLA, BFLA, auth, mass assignment, цены/заказы/корзина, ЮKassa/Сбер, 1С, injection, uploads, throttling, CORS/CSRF/headers, секреты, логи, admin_api).

**Вне границ:** исправление кода; нагрузочные тесты; реальные платежи/webhook к провайдерам; обращение к 1С; изменение БД/Git; полный аудит Frontend (кроме вызовов API, влияющих на выводы); E2E в браузере.

## 2. Методика проверки

1. Отправная точка — карта Блока № 1.  
2. Трассировка URL → View → Serializer → Service → Model для критичных доменов.  
3. Проверка `permission_classes`, `get_queryset` / object-level ownership, writable fields, payment/webhook trust model, 1C client SSRF/XXE controls.  
4. Сверка с существующими тестами **без** запуска (как индикатор намерений, не доказательство безопасности).  
5. Классификация Severity / Confidence / Status по шаблону SEC-XXX.

## 3. Полнота покрытия

| Область | Покрытие |
|---|---|
| Публичные/приватные API mounts (`api_urls` + app urls) | Полное перечисление маршрутов |
| Orders / cart / payments / eligibility / yookassa_service | Глубокое чтение реализации |
| users auth (JWT cookie, MFA claim, register, addresses) | Глубокое |
| admin_api permissions + users/orders/products ключевые views | Глубокое / выборочное |
| content reviews, promotions validate | Среднее |
| 1C client / url_utils / parser (defusedxml) | Среднее–глубокое |
| CORS/CSRF/production settings | Среднее–глубокое |
| Каждый serializer admin_api построчно | Частично |
| Management commands, все Celery paths | Частично |
| Live runtime / penetration | Не выполнялось |

**Оценка endpoints:** просмотрены все mounts `api/v1` (~базовые публичные группы + ~62 path-записи admin_api); детальный object-level разбор выполнен для orders/cart/payments/users/wishlist/addresses/content reviews/admin users&orders.

## 4. Карта API и механизмов доступа (сводка)

### Глобально (`config/settings/base.py`)

- Auth: `LenientJWTAuthentication`, `JWTCookieAuthentication`, `SessionAuthentication`.  
- Default permission: `IsAuthenticatedOrReadOnly` (переопределяется на views).  
- Throttles: anon/user + специализированные order/auth/cart/payment.  
- Axes на login; Argon2; JWT rotate+blacklist; iss/aud.

### Критичные паттерны доступа

| Endpoint-группа | Auth | Object ownership |
|---|---|---|
| `GET/POST /orders/` | GET: IsAuthenticated; POST: AllowAny | GET: filter `user` unless `is_staff` |
| `GET /orders/{id}/` | IsAuthenticated | queryset filter owner unless staff |
| `POST …/cancel|pay|payment` | AllowAny + `_can_access_order` / phone+order_number | staff OR owner OR guest knowledge |
| `/cart/*` | AllowAny | session/user cart via `get_or_create_cart`; item by `pk` **and** cart |
| `/wishlist/`, `/auth/addresses/` | IsAuthenticated | filter `request.user` |
| `/admin/*` | IsAuthenticated + IsStaff + AdminMfaVerified + group | staff RBAC |
| `/payments/yookassa/webhook/` | AllowAny, no auth | trust via YooKassa GET re-fetch |
| `/bonus/` | **не смонтирован** | — |

## 5. Результаты по направлениям

### 5.1–5.2 IDOR / BOLA

- Корзина: item mutate только при `cart=current` — **OK**.  
- Wishlist / addresses: queryset по user — **OK**.  
- Order detail (auth): owner/staff — **OK** для обычного user.  
- **Риск:** любой `is_staff` обходит owner-filter на list/detail/cancel/pay **без** admin_api MFA/групп (см. SEC-001).  
- Гостевой track/status/cancel/pay: knowledge factor `order_number`+`phone` (+ UUID для cancel/pay) — **by design**, остаточный риск утечки URL (SEC-006).

### 5.3 BFLA

- `admin_api` требует staff + MFA (если OTP) + ringoo_* group — **сильная модель**.  
- Обход MFA/групп через **публичный** `/api/v1/orders/` для staff — SEC-001.  
- Назначение `is_staff`/`groups` только superuser — **OK** (`UserAdminUpdateSerializer`).  
- Frontend роль не доверяется — **OK**.

### 5.4 Auth / sessions

- Cookie JWT + double-submit CSRF middleware — реализовано.  
- Logout blacklist refresh — есть.  
- Password login не выдаёт `admin_mfa` — **OK**.  
- Refresh сохраняет MFA claim осознанно (`AdminMfaAwareTokenRefreshSerializer` path).  
- Password reset / email verify flows — **не найдены** как публичные API (Info).  
- Lenient JWT: битый токен → гость на AllowAny — intentional UX; не IDOR сам по себе.

### 5.5 Mass assignment

- Register / me / OrderCreate: привилегированные поля не writable с клиента — **OK**.  
- Цены заказа пересчитываются с `Product.price` — **OK** (SEC defense confirmed).  
- `bonus_used` принудительно 0 — **OK**.  
- Review create: `is_approved` не в writable fields — **OK**; но чтение email — SEC-002.

### 5.6 Цены / корзина / заказы

- Server-side price resolution в `OrderCreateSerializer.validate` — **подтверждено**.  
- Online: `checkout_cart_id`, clear только после PAID через `clear_cart_after_successful_payment` — согласовано с B1 правилами.  
- Admin PATCH `status=cancelled` **не** вызывает `cancel_order_and_release_stock` — SEC-003.  
- Idempotency key глобальный в cache — FE использует `crypto.randomUUID()`; теоретический cross-user cache read при коллизии/фиксации ключа — SEC-007 (Low).

### 5.7 Платежи ЮKassa / Сбер

- Paid только после trusted API GET + amount/currency/metadata checks — **сильная защита**.  
- UniqueConstraint one paid per order + eligibility blocks — **OK**.  
- Webhook AllowAny без IP allowlist; защита = re-fetch (DoS/abuse — SEC-008 Info/Low).  
- Сбер callback token fail-closed вне DEBUG — **OK** при правильном env.  
- Return URL не считается оплатой — **OK** (poll sync).

### 5.8 1С

- Base URL нормализация, same-host redirect block, defusedxml — **OK против классического SSRF/XXE из клиента**.  
- Credentials из settings/env, не из user input.  
- Операции sync/import — серверные/management/Celery; обычный user не задаёт URL 1С через API — **не найдено** user-driven SSRF.  
- Резерв при создании заказа — side effect для любого checkout (бизнес, не привилегия).

### 5.9 Injection

- Raw SQL: health `SELECT 1`, test helpers — не user-controlled.  
- `defusedxml` для 1С XML.  
- ORM filters; ordering whitelist на orders list (`created_at` / default) — **OK**.  
- Subprocess только в test/scripts — вне prod request path.

### 5.10 Uploads / media

- Product images: PIL validate + WebP pipeline (admin).  
- Import xlsx size limit 8MB.  
- Media в DEBUG через django static; prod optional `SERVE_MEDIA`.  
- Публичные media — ожидаемо для каталога; чужие private docs через media — **не изучалось построчно все upload_to**.

### 5.11 Rate limiting

- Есть специализированные throttle scopes.  
- Review create **без** отдельного throttle_classes (только default anon) — SEC-009.  
- Webhook throttle 120/min — остаточный abuse.

### 5.12 CORS / CSRF / headers

- production.py fail-closed DEBUG/CORS_ALLOW_ALL/SECRET/ALLOWED_HOSTS/OTP.  
- JwtCookieCsrfMiddleware для cookie-mode unsafe methods.  
- YooKassa webhook не в CSRF exempt list middleware, но без JWT cookie + DRF csrf_exempt APIView — ожидаемо работает; остаточный Info.

### 5.13 Секреты

- `.env*` в `.gitignore`.  
- Default `SECRET_KEY` insecure в base — только если production module не используется (production запрещает).  
- Секреты в отчёт не выводились.  
- `PaymentSerializer` не отдаёт raw register_response — **OK**.

### 5.14 Логи / ПДн

- Login failures маскируют phone (`security_logging` / `mask_phone`).  
- TOTP codes не логируются.  
- Order track отдаёт полный `OrderSerializer` (ПДн) при знании номера+телефона — by design.  
- Reviews email публично — SEC-002.

## 6. Найденные уязвимости и замечания

### SEC-001 — Staff обходит MFA/RBAC admin_api через публичный Orders API

- **Severity:** High  
- **Confidence:** High  
- **Статус:** подтверждённая уязвимость (логика доступа в коде)  
- **Затронутые компоненты:** `OrderListCreateView.get`, `OrderDetailView`, `OrderCancelView`, `OrderPayView`, `_can_access_order`  
- **Файл:** `backend/apps/orders/views.py`; `backend/apps/payments/views.py`  
- **Строки:** ~77–81, 332–336, 497–500 (orders); ~74–101 (payments `_can_access_order`)  
- **Класс / функция:** `OrderListCreateView.get`, `OrderDetailView.get_queryset`, `OrderCancelView.post`, `_can_access_order`  
- **Доказательство:** при `request.user.is_staff` queryset заказов не фильтруется владельцем; cancel/pay разрешены staff без проверки `admin_permissions` / `AdminMfaVerified`. admin_api при `ADMIN_OTP_ENABLED` требует MFA+группу, публичный `/api/v1/orders/` — нет.  
- **Сценарий эксплуатации:** скомпрометированный или низкопривилегированный staff-аккаунт (даже без ringoo_* и без TOTP) получает JWT и читает/ищет все заказы (телефон, ФИО, адрес), отменяет чужие, инициирует pay/status.  
- **Предварительные условия:** учётная запись с `is_staff=True` и возможность логина.  
- **Возможный ущерб:** массовая утечка ПДн заказов; деструктивные действия по заказам в обход MFA.  
- **Рекомендация:** на публичных customer endpoints не давать staff «все заказы»; staff-операции только через `admin_api` с MFA+группами; либо требовать те же permissions на orders API.  
- **Необходимые тесты:** staff без группы/MFA → 403 на list all / detail чужого / cancel чужого; staff с ringoo_orders+MFA → доступ только admin routes.

### SEC-002 — Публичное API отзывов раскрывает email и неодобренные отзывы

- **Severity:** Medium  
- **Confidence:** High  
- **Статус:** подтверждённая уязвимость  
- **Затронутые компоненты:** `ReviewViewSet`, `ReviewSerializer`  
- **Файл:** `backend/apps/content/views.py`, `backend/apps/content/serializers.py`  
- **Строки:** views ~154–171; serializers ~135–160  
- **Класс / функция:** `ReviewViewSet.get_queryset`, `ReviewSerializer`  
- **Доказательство:** `?is_approved=false` возвращает неодобренные отзывы любому клиенту; сериализатор включает `email` (и `name`) в публичном ответе даже для одобренных.  
- **Сценарий эксплуатации:** `GET /api/v1/content/reviews/?is_approved=false` (и/или по product) → сбор email/комментариев до модерации; также сбор email с витрины.  
- **Предварительные условия:** анонимный доступ к API.  
- **Возможный ущерб:** утечка ПДн; спам; репутационный риск.  
- **Рекомендация:** запретить публичный filter `is_approved=false`; убрать `email` из публичного serializer (оставить в admin).  
- **Необходимые тесты:** anon не видит unapproved; response без email.

### SEC-003 — Admin смена статуса на `cancelled` не освобождает резерв склада

- **Severity:** Medium  
- **Confidence:** High  
- **Статус:** подтверждённая логическая/целостностная уязвимость (abuse staff)  
- **Затронутые компоненты:** `OrderAdminUpdateView`, `cancel_order_and_release_stock`  
- **Файл:** `backend/apps/admin_api/views/orders.py`; `backend/apps/orders/services/__init__.py`  
- **Строки:** admin ~21–91; services ~15–48  
- **Класс / функция:** `OrderAdminUpdateView.patch` vs `cancel_order_and_release_stock`  
- **Доказательство:** user cancel вызывает `cancel_order_and_release_stock`; admin PATCH только `serializer.save()` статуса без release/1C cancel enqueue.  
- **Сценарий эксплуатации:** оператор/атакующий staff с `ringoo_orders` переводит заказ в cancelled через admin API → резерв остаётся → искусственный дефицит.  
- **Предварительные условия:** доступ admin_api orders (MFA+группа при OTP).  
- **Возможный ущерб:** рассинхрон остатков, отказ в продажах, рассинхрон с 1С.  
- **Рекомендация:** при переходе в cancelled вызывать тот же сервис отмены/release; тесты на reserved quantity.  
- **Необходимые тесты:** admin cancel → reserved уменьшается; повтор идемпотентен.

### SEC-004 — Создание отзывов без выделенного throttle (спам / флуд)

- **Severity:** Low  
- **Confidence:** High  
- **Статус:** потенциальная уязвимость / злоупотребление  
- **Затронутые компоненты:** `ReviewViewSet` create  
- **Файл:** `backend/apps/content/views.py`  
- **Строки:** ~145–182 (нет `throttle_classes` на ViewSet; другие content views имеют read throttles)  
- **Доказательство:** create доступен AllowAny; лимит только default `anon: 100/hour`.  
- **Сценарий эксплуатации:** массовый POST отзывов с поддельными name/email.  
- **Предварительные условия:** доступ к API.  
- **Возможный ущерб:** засор модерации, нагрузка DB.  
- **Рекомендация:** отдельный throttle scope + капча/лимит на product.  
- **Необходимые тесты:** превышение лимита → 429.

### SEC-005 — Глобальный namespace `X-Idempotency-Key` без привязки к клиенту

- **Severity:** Low  
- **Confidence:** Medium  
- **Статус:** потенциальная уязвимость  
- **Затронутые компоненты:** `OrderListCreateView.post`  
- **Файл:** `backend/apps/orders/views.py`  
- **Строки:** ~135–143, 312–318  
- **Доказательство:** cache key `order_idempotency:{key}` без user/IP; повтор возвращает чужой cached response. FE обычно шлёт `crypto.randomUUID()`.  
- **Сценарий эксплуатации:** фиксация/угадывание ключа → получение JSON чужого заказа (ПДн) или подмена ответа создания.  
- **Предварительные условия:** знание/контроль ключа жертвы.  
- **Возможный ущерб:** точечная утечка ответа заказа.  
- **Рекомендация:** включать hash(user_id|session|ip) в cache key; короткоживущий TTL уже есть.  
- **Необходимые тесты:** разные клиенты с одним key не получают чужие данные.

### SEC-006 — Гостевой доступ к заказу/оплате/отмене по knowledge factor (остаточный риск)

- **Severity:** Low (Info→Low)  
- **Confidence:** High  
- **Статус:** потенциальная уязвимость / принятый риск дизайна  
- **Затронутые компоненты:** track, status, cancel, pay, payment status  
- **Файл:** `orders/views.py`, `payments/views.py`  
- **Доказательство:** доступ при совпадении `order_number`+`phone` (+ UUID в path для pay/cancel). UUID часто в return URL.  
- **Сценарий эксплуатации:** утечка SMS/email + ссылки return → отмена или pay status чужого заказа.  
- **Предварительные условия:** знание секретов заказа.  
- **Возможный ущерб:** точечный доступ к одному заказу.  
- **Рекомендация:** усилить guest token (signed), не светить полный serializer лишним полям; rate limit уже есть (`order_track` 5/min).  
- **Необходимые тесты:** без phone → 404; throttle.

### SEC-007 — Webhook ЮKassa AllowAny без IP allowlist (зависимость от re-fetch)

- **Severity:** Info / Low  
- **Confidence:** High  
- **Статус:** потенциальная уязвимость (DoS/abuse), **не** обход оплаты при текущей логике  
- **Затронутые компоненты:** `YooKassaWebhookView`, `handle_yookassa_webhook`  
- **Файл:** `payments/views.py`, `yookassa_service.py`  
- **Доказательство:** webhook принимает любой POST; paid ставится только после GET к API и проверок amount/metadata.  
- **Сценарий эксплуатации:** флуд webhook → нагрузка на worker/API ЮKassa.  
- **Рекомендация:** IP allowlist ЮKassa / mTLS / доп. shared secret если появится у провайдера; сохранить re-fetch.  
- **Необходимые тесты:** forged succeeded payload без реального YK → не paid (уже покрыто тестами проекта частично).

### SEC-008 — Dormant bonus admin views с ослабленными permissions

- **Severity:** Info  
- **Confidence:** High  
- **Статус:** потенциальная (сейчас URL не смонтированы)  
- **Файл:** `backend/apps/admin_api/views/bonus.py`; `config/api_urls.py` (bonus commented)  
- **Доказательство:** views используют `[IsStaff]` без MFA/group; маршруты закомментированы.  
- **Рекомендация:** при включении — `admin_permissions(...)`; не монтировать со старыми perms.

### SEC-009 — Отсутствие публичного password-reset / recovery API

- **Severity:** Info  
- **Confidence:** High  
- **Статус:** не уязвимость конфиденциальности; пробел доступности/процесса  
- **Доказательство:** в users urls/views не найден reset-password endpoint (поиск по коду).  
- **Рекомендация:** при появлении — токены одноразовые, throttle, без user enumeration.

## 7. Проверенные механизмы защиты (работают корректно по коду)

| Механизм | Доказательство |
|---|---|
| Пересчёт цен заказа на сервере | `OrderCreateSerializer.validate` подставляет `Product.price`, игнорирует client total/delivery |
| Корзина: цена с каталога/цвета | `CartItemCreateView` `unit_price` из product/color |
| Object-level cart items | filter `pk` + `cart` |
| Wishlist/addresses ownership | queryset `user=request.user` |
| Online cart retention / clear after PAID | `checkout_cart_id` + `clear_cart_after_successful_payment` |
| ЮKassa paid trust model | GET re-fetch + amount/currency/metadata + unique paid |
| Eligibility / repay gates | `payments/eligibility.py` |
| admin_api RBAC + MFA claim | `admin_permissions`, `AdminMfaVerified` |
| is_staff/groups только superuser | `UserAdminUpdateSerializer.validate_*` |
| 1C URL normalize + redirect same-host + defusedxml | `url_utils`, `client`, `parser` |
| Production fail-closed | `config/settings/production.py` |
| Axes + login throttle | settings + `AuthLoginAnonThrottle` |
| JWT rotate/blacklist | SIMPLE_JWT + LogoutView |
| PaymentSerializer без сырых bank payloads | read-only безопасный набор полей |

## 8. Отдельный аудит Django Admin и admin_api

- Django Admin: path из `ADMIN_SITE_URL_PATH`; OTPAdminSite при `ADMIN_OTP_ENABLED`.  
- admin_api: ~62 path; почти везде `admin_permissions(group)` или dashboard `HasAnyAdminGroup`.  
- Исключение/риск: публичный orders API для staff (SEC-001); bonus views dormant (SEC-008); admin cancel без release (SEC-003).  
- Массовые цены/import — за group catalog + MFA; xlsx size limit.  
- Обычный user без staff → 403 на `/api/v1/admin/*` (по permission-классам; runtime не гонялся).

## 9. Отдельный аудит ЮKassa и платежей

- Цепочка initiate → redirect → webhook/poll → sync GET → PAID → cart clear + 1C enqueue — согласована.  
- Подделка webhook **недостаточна** для PAID без ответа ЮKassa API (при корректных credentials).  
- Двойная оплата блокируется eligibility + DB constraint.  
- Сбер код жив, выбор провайдера: YK wins; оба флага → warning, только YK.  
- Непроверено runtime: реальная доставка webhook, clock skew, частичные refunds.

## 10. Отдельный аудит интеграции с 1С

- Клиент серверный; user API не принимает произвольный 1C URL.  
- XXE: defusedxml.  
- SSRF: normalize path suffix + block foreign redirects.  
- TLS: зависит от `ONE_C_API_BASE_URL` (http допустим нормализатором схемы — **операционный риск**, если в prod задан http) — Info/конфиг.  
- Sync/cancel через Celery; флаги `ONE_C_*`.

## 11. Непроверенные области

- Полный построчный разбор всех admin serializers/filters.  
- Все management commands.  
- Фактическое содержимое production env на VPS (только код/examples).  
- Runtime IDOR тестами против живой БД.  
- Поведение при одновременных concurrent pay (частично видно select_for_update; гонки не доказаны динамически).  
- Полный анализ логов Docker/ELK retention.  
- Frontend XSS/CSP (вне scope B2).  
- Сравнение live PostgreSQL constraints vs migrations.

## 12. Сводная таблица по severity

| ID | Severity | Confidence | Статус |
|---|---|---|---|
| SEC-001 | High | High | подтверждена |
| SEC-002 | Medium | High | подтверждена |
| SEC-003 | Medium | High | подтверждена |
| SEC-004 | Low | High | потенциальная |
| SEC-005 | Low | Medium | потенциальная |
| SEC-006 | Low | High | принятый/остаточный риск |
| SEC-007 | Info/Low | High | потенциальная (не обход оплаты) |
| SEC-008 | Info | High | dormant |
| SEC-009 | Info | High | пробел процесса |

**Итого:** Critical 0; High 1; Medium 2; Low 3; Info 3.

## 13. Приоритет исправлений (после согласования)

1. **SEC-001** — убрать staff bypass на customer Orders/Payments API / выровнять с MFA+RBAC.  
2. **SEC-002** — закрыть unapproved filter и email в публичных reviews.  
3. **SEC-003** — единый путь отмены с release stock из admin.  
4. SEC-004 / SEC-005 — hardening.  
5. SEC-006–009 — по риск-аппетиту.

## 14. Общий вывод о безопасности Backend/API

Базовые коммерческие контроли (серверный пересчёт цен, object-level корзина/wishlist/addresses, trust model ЮKassa с re-fetch, admin_api MFA+группы, production fail-closed, 1C XXE/SSRF hardening) выглядят **осознанно спроектированными**.

Главный подтверждённый разрыв — **несогласованность модели staff**: жёсткий admin_api vs «полный доступ ко всем заказам» через обычный `/api/v1/orders*` для любого `is_staff` (SEC-001). Второй — **ПДн в публичных отзывах** (SEC-002). Третий — **целостность склада при admin-отмене** (SEC-003).

Обход оплаты через поддельный return URL или «голый» webhook **по коду не подтверждён**. Критических RCE/SQLi/массового privilege escalation через register **не найдено** в просмотренном коде.

---

### Метаданные завершения Блока № 2

- **Дата:** 2026-11-05  
- **Статус:** завершён (статический)  
- **Проверенные компоненты (основные):** `config/settings/{base,production,development}.py`, `config/api_urls.py`, `config/csrf_api.py`, `config/views.py`, `apps/orders/{views,serializers,services}`, `apps/cart/{views,serializers,checkout_clear}`, `apps/payments/{views,services,yookassa_service,eligibility,serializers,models}`, `apps/users/{views,serializers,authentication,admin_mfa}`, `apps/admin_api/{permissions,urls,views/orders,users,products(partial),bonus}`, `apps/content/{views,serializers}`, `apps/wishlist/views`, `integrations/onec/{client,url_utils,parser}`, `.gitignore`  
- **Непроверенные:** см. §11  
- **Ограничения:** без runtime атак, без внешних API, без изменения данных  
- **Подтверждение:** исходный код приложения, конфигурации (кроме этого отчёта), БД и Git state **не изменялись** аудитом; разрешён только файл `docs/audit/RINGO_FULL_AUDIT.md`  
- **Подтверждение накопления:** раздел Блока № 1 сохранён выше; Блок № 2 добавлен в конец файла без удаления предыдущего содержимого

---

# БЛОК № 3 — ПОЛНЫЙ ФУНКЦИОНАЛЬНЫЙ АУДИТ И ПРОВЕРКА БИЗНЕС-ЛОГИКИ

**Дата аудита:** 2026-11-05  
**Статус блока:** завершён (статический анализ кода Frontend+Backend; runtime checkout/оплата/1С/изменение БД не выполнялись)  
**Режим:** READ-ONLY; изменён только этот накопительный файл.  
**Контекст:** использованы выводы Блоков № 1–2; SEC-001/002/003 не «исправлялись», а прослежены функциональные последствия.

## 1. Цель и границы

Цель — объективно установить корректность бизнес-логики магазина: каталог → корзина → заказ → оплата → склад/1С → ЛК, соответствие FE↔BE, устойчивость к ошибкам и гонкам.

**Вне границ:** правки кода; реальные заказы/платежи/1С; нагрузочные тесты; полный UI E2E в браузере; исправление SEC-*.

## 2. Методика

1. Чтение RINGO_FULL_AUDIT.md (B1–B2).  
2. Трассировка ключевых сценариев FE → API → serializer/view → service → model → Celery/1C/YooKassa.  
3. Сопоставление заявленного UI с фактическими endpoints.  
4. Фиксация FUNC-XXX только при доказательстве по коду.  
5. Тесты читались как индикатор намерений, **не запускались**.

## 3. Карта пользовательских сценариев (прослежено по коду)

| # | Сценарий | Цепочка (кратко) | Вердикт по коду |
|---|---|---|---|
| S1 | Каталог/карточка | FE hooks → /products/ → active filters + cache | Работает; кэш инвалидируется signals |
| S2 | Add/update/remove cart | useCart → /cart/* → session/user cart | Работает; optimistic + rollback |
| S3 | Login merge cart | login → BE merge_guest_cart_into_user → FE invalidate cart | Работает |
| S4 | Checkout non-online | create order → reserve → wipe cart items → success | Работает |
| S5 | Checkout online | create + checkout_cart_id → pay → PSP → return poll → PAID clear | В целом корректно; см. FUNC-001 |
| S6 | Repay | can_pay + POST .../pay/ | Работает по eligibility |
| S7 | Cancel user | API + order-status UI; ЛК detail без кнопки | Частично FE |
| S8 | Admin cancel | PATCH status only | **Ошибка** (SEC-003 / FUNC-002) |
| S9 | Reviews public | AllowAny list/create | **Ошибка ПДн** SEC-002 / FUNC-008 |
| S10 | Bonuses | signals начисляют; API/FE off | Заготовка/рассинхрон |
| S11 | Promo at checkout | validate API есть; в заказе не применяется | Частично / заглушка UI |

## 4. Таблица функциональности

| Функция | Backend | Frontend | Интеграция | Статус | Проблемы |
|---|---|---|---|---|---|
| Каталог/фильтры/поиск | Да | Да | — | Реализовано и корректно по коду | Кэш/устаревшая цена в корзине — см. FUNC-003 |
| Карточка + цвета + stock | Да | Да | Stock/1C codes | Реализовано и корректно по коду | — |
| Корзина guest/user + merge | Да | Да | — | Реализовано и корректно по коду | Clear по product_id — FUNC-004 |
| Online cart retention | Да | Да (invalidate after PAID) | YK/Sber | Реализовано и корректно по коду | — |
| Checkout | Да | Да | Stock reserve | Реализовано, но есть ошибки | Stale UX price; expire YK — FUNC-001/003 |
| Оплата ЮKassa | Да | Да | YK | Реализовано и корректно по коду (trust model) | expire без YK sync — FUNC-001 |
| Repay | Да | Да (can_pay) | YK | Реализовано и корректно по коду | — |
| Отмена заказа | Да | Частично (order-status) | release+1C cancel | Реализовано частично | Нет кнопки в ЛК detail; admin path — FUNC-002/005 |
| Track/status guest | Да | Да | — | Реализовано и корректно по коду | Knowledge-factor (SEC-006) |
| Профиль / адреса / export / delete | Да | Да | — | Реализовано и корректно по коду | Нет смены пароля/reset |
| Wishlist | Да | Да | — | Реализовано и корректно по коду | — |
| Reviews + rating | Да | Да | signals rating | Реализовано, но есть ошибки | SEC-002 / FUNC-008 |
| Promotions list | Да | Да | — | Реализовано и корректно по коду | — |
| PromoCode на заказ | validate only | заглушка checkout | — | Реализовано частично | FUNC-006 |
| Бонусы | models+signals+services | «скоро» | API off | Отключено / заготовка | FUNC-007 |
| Доставка cost | всегда 0 | показывает | — | Реализовано частично | Бесплатная по коду |
| 1C catalog/orders | Да (flags) | admin import UI | HTTP | Реализовано частично | зависит от env; dry-run/apply — commands |
| Admin orders/stock/catalog | Да + MFA/RBAC | Да | — | Реализовано, но есть ошибки | FUNC-002; staff leak SEC-001 |

## 5. Каталог товаров

**ПОДТВЕРЖДЕНО**

- Список/деталь: только is_active=True и category__is_active=True (products/views.py ProductList/Detail).  
- Сортировки/фильтры: pply_catalog_filters, ordering popular/price/rating/created_at.  
- Неактивный товар: 404 на detail; в корзине может остаться до checkout; на create заказа OrderCreateSerializer отсекает неактивные.  
- Остатки: Stock.available_quantity; на карточке FE vailability_status / stock list.  
- Резерв при заказе только в выбранном store_id (plan_and_reserve_at_store) — без поиска по сети.  
- Кэш detail/list инвалидируется signals (products/signals.py).  
- Цена в корзине = price_at_add на момент add; **заказ** берёт актуальную Product.price — возможное расхождение UI корзины и итога (FUNC-003).

## 6. Корзина

**ПОДТВЕРЖДЕНО корректное**

- Guest: session_key; user: FK user (Cart.get_or_create_cart).  
- Merge: merge_guest_cart_into_user складывает qty по (product, store, color); retarget checkout_cart_id; login FE invalidates cart.  
- Item mutate scoped to current cart.  
- Online: cart не wipe при create; clear после PAID вычитает qty по OrderItem (checkout_clear.py).  
- Return URL: FE инвалидирует cart **только если** payment.status === 'paid' (payment/return/page.tsx ~71–76).  
- Checkout online: не clearCart на FE до PAID; invalidate при redirect — backend корзина ещё полная.

**Риск FUNC-004:** clear матчит только product_id, порядок created_at — при нескольких цветах/магазинах одного SKU может уменьшиться «не та» линия (qty в сумме корректен для SKU, состав color/store может сместиться).

## 7. Оформление заказа

**ПОДТВЕРЖДЕНО**

- FE: rom_cart: true + snapshot items + idempotency UUID (checkout/page.tsx ~392–421).  
- BE: цены/итог пересчёт в serializer; delivery_cost=0; onus_used→0.  
- Транзакция: Order + OrderItems + reserve в одном tomic; при InsufficientStockError rollback.  
- Online: checkout_cart_id; non-online: cart.items.delete().  
- После create: Celery notify + enqueue 1C paid=False.  
- Двойной submit: idempotency cache + mutation isPending.  
- Pay fail после create: redirect fail, cart retained (online).

**Частично:** промокоды в UI — заглушка (FUNC-006). Доставка без тарифов.

## 8. Жизненный цикл заказа

| Текущий | Действие | Новый | Кто | Побочные эффекты |
|---|---|---|---|---|
| (create) | POST /orders/ | 
ew | user/guest | reserve stock; 1C sync unpaid; online keeps cart |
| 
ew | YK/Sber PAID | confirmed | payment sync | cart clear; 1C paid enqueue; bonus signal |
| 
ew/confirmed | user cancel API | cancelled | owner/guest/staff | **release** + 1C cancel enqueue |
| 
ew/confirmed | admin PATCH cancelled | cancelled | ringoo_orders | **без release** (SEC-003 / FUNC-002) |
| 
ew/confirmed | expire unpaid timeout | cancelled | Celery | release; payments→expired; **YK не sync перед отменой** (FUNC-001) |
| confirmed | admin → in_progress | in_progress | admin | — |
| in_progress | admin → completed/cancelled | … | admin | cancelled без release |
| completed/cancelled | admin transitions | запрещены | — | OrderAdminUpdateSerializer |

Повторная отмена user: идемпотентна в cancel_order_and_release_stock.  
Оплаченный: eligibility блокирует pay; cancel оплаченного confirmed всё ещё возможен user API (бизнес-риск — FUNC-009).

## 9. Личный кабинет

| Функция | FE | BE | Статус |
|---|---|---|---|
| Login/register/logout | Да | Да | OK |
| Profile / marketing | Да | PATCH me | OK |
| Addresses CRUD | Да | Да | OK |
| Export / delete account | Да | Да | OK |
| Orders list/detail | Да | Да | OK |
| Repay | Да | pay+can_pay | OK |
| Cancel | order-status | cancel API | Частично (нет в detail ЛК) — FUNC-005 |
| Password change/reset | Нет | Нет | Не реализовано |
| Bonuses UI | заглушка | signals+API off | FUNC-007 |
| Rate orders | profile/order-rate | rate API | OK |

## 10. Повторная оплата

- evaluate_order_payment_eligibility: online + new/confirmed + нет blocking payment; resume registered/pending/created.  
- FE кнопка: order.can_pay && isOnlinePaymentUiEnabled().  
- Initiate: reuse form_url после sync; dual paid blocked constraint.  
- Сумма = Order.total_amount (не клиент).  
- Новый Order не создаётся.  
**Корректно по коду** при условии работоспособности провайдера.

## 11. ЮKassa

Цепочка create Payment → API create → confirmation_url → webhook/poll → GET verify → PAID → cart clear + 1C — **согласована**.  
Return URL ≠ оплата — **OK**.  
Поздняя оплата после cancel → pply_late_payment_policy (YK reverse→manual).  
**FUNC-001:** expire_unpaid_online_orders перед отменой синкает только платежи с sber_order_id, не YooKassa; при задержке webhook заказ может отмениться, затем late-policy.  

econcile_open_payments (каждые 3 мин) синкает YK — смягчает, но окно гонки с expire (5 мин task, timeout 20 мин) остаётся.

## 12. Склад и резервирование

Схема: quantity − 
eserved_quantity = available → reserve_atomic при create → release при user cancel/expire → (не) при admin cancel.  
Гонка двух покупателей: select_for_update + atomic reserve — защита по коду есть; runtime не проверялся.  
1C ошибка sync после create: локальный заказ и резерв остаются; sync_status error/blocked/pending_review.  
Отрицательный reserved: release использует atomic guards 
eserved_quantity__gte.

## 13. Интеграция с 1С

- Catalog: parser/importer dry-run/apply (management; не публичный user API).  
- Orders: enqueue sync paid false/true; cancel task; guest registration safeguards.  
- Без ONE_C_* flags — sync disabled paths.  
- Повреждение каталога «случайным apply» через публичный API покупателя — **не найдено**.  
Admin product import — отдельный xlsx path, не XML 1C.

## 14. Отзывы

- Create: AllowAny; is_approved не writable.  
- Rating товара: только approved (content/signals.py).  
- **SEC-002 / FUNC-008:** публичный ?is_approved=false и поле email в list — влияет на витрину/модерацию (утечка до публикации).  
Редактирование/удаление своего отзыва покупателем — **не найдено** в публичном API.

## 15. Избранное и бонусы

- Wishlist: auth-only, ownership OK; FE hooks.  
- Bonus: AppConfig подключает signals → начисление при confirmed в БД; публичный API закомментирован; FE «скоро». Spend через checkout отключён (onus_used→0). **FUNC-007**.

## 16. Доставка и оплата

- Delivery: pickup | delivery; адрес required для delivery; store обязателен.  
- delivery_cost всегда 0 на сервере.  
- Payment: cash | card_on_delivery | bank_transfer | online.  
- Региональных ограничений в коде не найдено.  
- Изменение delivery/payment после create через customer API — **не найдено**.

## 17. Frontend ↔ Backend

| Страница | Соответствие |
|---|---|
| Catalog/product | Соответствует |
| Cart/checkout | Соответствует; promo UI честно говорит «после API» |
| Payment return/fail | Соответствует trust model |
| Orders detail repay | Соответствует can_pay |
| Cancel | API есть; UI в основном order-status, не карточка ЛК |
| Profile bonuses | UI заглушка vs BE signals |
| Admin | Соответствует admin_api |

Optimistic cart: rollback onError — OK.  
Двойные запросы checkout: закрыты isPending + idempotency.

## 18. Транзакции и ошибки

| Операция | Атомарность | При сбое |
|---|---|---|
| Create order+items+reserve | atomic | полный rollback |
| YK paid + cart clear | paid в txn; clear on_commit try/except | paid сохранён, clear fail → лог (корзина может остаться) |
| 1C sync | claim + HTTP вне long lock | статусы error/retry |
| Admin cancel | только status | резерв «висит» FUNC-002 |
| Expire unpaid | cancel+release | без YK pre-sync FUNC-001 |

## 19. Найденные проблемы

### FUNC-001 — Expire unpaid не сверяет ЮKassa перед отменой заказа

- **Приоритет:** High  
- **Уверенность:** High  
- **Статус:** подтверждённая ошибка  
- **Затронутая функция:** таймаут онлайн-оплаты / Celery expire  
- **Пользовательский сценарий:** оплата в ЮKassa прошла, webhook задержался > ONLINE_PAYMENT_TIMEOUT_MINUTES; beat отменяет заказ и снимает резерв; позже webhook/late policy  
- **Файлы:** ackend/apps/payments/services.py  
- **Строки:** ~783–856 (цикл sync только .exclude(sber_order_id…) ~811–818)  
- **Класс / функция:** expire_unpaid_online_orders  
- **Ожидаемое поведение:** перед отменой сверить активный платёж с активным провайдером (в т.ч. YooKassa)  
- **Фактическое поведение:** pre-sync только для Sber sber_order_id; YK payments пропускаются  
- **Причина:** устаревшая ветка под Сбер при добавлении ЮKassa  
- **Последствия для покупателя:** заказ cancelled при уже оплаченном; ручная/late обработка  
- **Последствия для магазина:** needs_review, рассинхрон склада/1С, поддержка  
- **Связанные находки:** B2 платежный trust model (корректный webhook); усиливает operational риск  
- **Рекомендация:** перед cancel вызывать sync_payment_status / YK sync для open payments заказа  
- **Тесты:** YK pending+succeeded remote → expire не cancels; unit с mock client  

### FUNC-002 — Admin PATCH cancelled без release/1C cancel (расширение SEC-003)

- **Приоритет:** High  
- **Уверенность:** High  
- **Статус:** подтверждённая ошибка  
- **Затронутая функция:** админ-смена статуса / склад / 1С  
- **Сценарий:** оператор отменяет через /api/v1/admin/orders/{id}/  
- **Файлы:** ackend/apps/admin_api/views/orders.py ~57–91; сравнить orders/services/__init__.py cancel_order_and_release_stock  
- **Ожидаемое:** как user cancel — release + enqueue 1C cancel  
- **Фактическое:** только status=cancelled  
- **Последствия:** «зависший» reserved; 1С может считать заказ активным  
- **Связанные:** **SEC-003**  
- **Рекомендация:** единый cancel service из admin update  
- **Тесты:** reserved↓; onec cancel enqueued  

### FUNC-003 — Расхождение суммы корзины (price_at_add) и суммы заказа (актуальный Product.price)

- **Приоритет:** Medium  
- **Уверенность:** High  
- **Статус:** подтверждённая ошибка UX/бизнес-ожиданий (не дыра безопасности цен)  
- **Файлы:** cart/views.py (price_at_add); orders/serializers.py validate (~235–255); FE checkout показывает cart.total_amount  
- **Ожидаемое:** покупатель видит ту же сумму, что спишется  
- **Фактическое:** заказ пересчитывается по каталогу; корзина может показывать старую цену  
- **Последствия:** споры, неожиданная сумма на оплате  
- **Рекомендация:** пересчёт витрины корзины / предупреждение / lock price policy  
- **Тесты:** изменение Product.price между add и checkout  

### FUNC-004 — Очистка корзины после оплаты игнорирует color/store

- **Приоритет:** Medium  
- **Уверенность:** High  
- **Статус:** подтверждённая ошибка краевого сценария  
- **Файл:** ackend/apps/cart/checkout_clear.py ~99–130  
- **Ожидаемое:** вычитать позиции, соответствующие составу заказа (product+атрибуты)  
- **Фактическое:** агрегат по product_id, FIFO created_at  
- **Последствия:** при двух цветах одного товара после оплаты может уменьшиться «другой» цвет  
- **Связанные:** B1 правило retention в целом соблюдено по qty  
- **Рекомендация:** учитывать color/store или snapshot line keys  
- **Тесты:** два color одного product; clear затрагивает ожидаемые  

### FUNC-005 — Отмена заказа в ЛК: API есть, кнопки на карточке заказа нет

- **Приоритет:** Medium  
- **Уверенность:** High  
- **Статус:** подтверждённая ошибка соответствия FE↔BE  
- **Файлы:** orders.service.ts cancelOrder; UI order-status/OrderStatusContent.tsx; отсутствует в orders/[id]/page.tsx  
- **Ожидаемое:** отмена из карточки заказа в ЛК  
- **Фактическое:** отмена через страницу проверки статуса  
- **Последствия:** пользователь не находит действие  
- **Рекомендация:** кнопка cancel на detail при new/confirmed  

### FUNC-006 — Промокоды не влияют на сумму заказа

- **Приоритет:** Low  
- **Уверенность:** High  
- **Статус:** подтверждённая частичная реализация  
- **Файлы:** promotions validate API; OrderCreateSerializer без promo; checkout UI ~874 «появятся после…»  
- **Ожидаемое (если маркетинг обещает скидки):** применение при checkout  
- **Фактическое:** только validate / витрина promotions  
- **Рекомендация:** либо скрыть validate от ожиданий, либо внедрить server apply  

### FUNC-007 — Бонусы начисляются в БД при API/UI отключённых

- **Приоритет:** Low  
- **Уверенность:** High  
- **Статус:** подтверждённая рассинхронизация  
- **Файлы:** onus/apps.py ready signals; onus/signals.py; pi_urls bonus commented; ProfileContent «скоро»  
- **Последствия:** скрытые балансы; путаница при будущем включении  
- **Рекомендация:** feature-flag signals вместе с API или документировать как silent accrual  

### FUNC-008 — Публичные отзывы: unapproved + email (функциональный эффект SEC-002)

- **Приоритет:** Medium  
- **Уверенность:** High  
- **Статус:** подтверждённая ошибка  
- **Связанные:** **SEC-002**  
- **Функциональный эффект:** модерация обходится чтением; email на витрине; рейтинг товара считает только approved (OK), но список может показывать черновики через query  

### FUNC-009 — User/guest могут отменить confirmed заказ (в т.ч. после оплаты)

- **Приоритет:** Medium  
- **Уверенность:** High  
- **Статус:** потенциальная бизнес-ошибка (зависит от политики)  
- **Файл:** OrderCancelView — статусы new|confirmed; paid online → status confirmed  
- **Фактическое:** cancel API не проверяет Payment.STATUS_PAID  
- **Последствия:** отмена оплаченного → late payment / ручная сверка; деньги vs склад  
- **Рекомендация:** запретить cancel при paid / только admin+refund flow  

### FUNC-010 — Staff видит все заказы через customer API (функциональный эффект SEC-001)

- **Приоритет:** High (как процессный/доступ)  
- **Уверенность:** High  
- **Статус:** подтверждено (B2); здесь — влияние на операции  
- **Связанные:** **SEC-001**  
- **Эффект:** сотрудники без MFA/групп работают с полным списком заказов/ПДн через не-admin UI/API  

## 20. Корректно реализованные механизмы

1. Server-side пересчёт цен заказа (anti price-tamper).  
2. Online cart retention + clear only after PAID + FE invalidate only on paid.  
3. Atomic reserve at selected store.  
4. YooKassa paid после trusted GET + amount/metadata.  
5. Payment eligibility / unique paid constraint / repay UX.  
6. Guest↔user cart merge + checkout_cart retarget.  
7. Idempotency key на create (FE UUID).  
8. Order admin transition matrix (кроме side effects cancel).  
9. Wishlist ownership.  
10. Product cache invalidation signals.

## 21. Непроверенные области

- Runtime гонки двух checkout на последний товар.  
- Реальный webhook delay / Celery timing на стенде.  
- Полный dry-run/apply 1C catalog на живых данных.  
- Все admin bulk import краевые случаи.  
- Смена пароля (отсутствует — подтверждено отсутствием).  
- E2E визуальные состояния всех empty/error.  
- Полный вывод explore-агентов FE/BE (параллельный разбор) — ключевые пути сверены напрямую.

## 22. Сводка по приоритетам

| Приоритет | ID |
|---|---|
| High | FUNC-001, FUNC-002, FUNC-010 (→SEC-001) |
| Medium | FUNC-003, FUNC-004, FUNC-005, FUNC-008 (→SEC-002), FUNC-009 |
| Low | FUNC-006, FUNC-007 |
| Critical | 0 |

## 23. Рекомендуемый порядок будущих исправлений (после согласования)

1. FUNC-001 (expire ↔ YooKassa sync).  
2. FUNC-002 / SEC-003 (единый cancel+release).  
3. FUNC-009 (политика cancel после paid).  
4. SEC-001 / FUNC-010 (staff access model).  
5. SEC-002 / FUNC-008 (reviews).  
6. FUNC-003–005 (UX/корзина/отмена в ЛК).  
7. FUNC-006–007 (promo/bonus product decisions).

---



### Уточнение B3.1 — дополнение после параллельного разбора FE/BE (без перезаписи FUNC-*)

Источники уточнения (read-only): [Backend functional audit](aa49a251-926f-429a-8e60-eb5c7bdfb634), [Frontend functional audit](523bfdd5-461f-48f5-8472-d75b20cd47ae). Ниже — только новые или усиленные факты; предыдущие FUNC/SEC не удалялись.

#### FUNC-011 — Цвет выбранный в корзине не попадает в заказ

- **Приоритет:** Medium  
- **Уверенность:** High  
- **Статус:** подтверждённая ошибка / пробел модели  
- **Доказательство:**  
  - FE checkout отправляет items: { product_id, quantity } без color — rontend/src/app/checkout/page.tsx (~404–407).  
  - OrderItemCreateSerializer / модель OrderItem **не содержат** поля color (поиск по pps/orders — color не найден).  
  - Цена заказа берётся из Product.price, не из color.effective_price() / price_at_add (orders/serializers.py validate).  
- **Связь:** усиливает FUNC-003 (расхождение сумм) и FUNC-004 (clear по product без color); цвет живёт только в корзине.  
- **Последствия:** комплектация/1С/склад не знают выбранный цвет; возможна неверная серия/ожидание покупателя.  
- **Рекомендация (позже):** поле color (или snapshot) на OrderItem + передача с FE + учёт в цене/резерве при необходимости.

#### Усиление FUNC-002 / SEC-003 — тот же пробел в Django Admin

- Помимо dmin_api PATCH: OrderAdmin.save_model (orders/admin.py ~83–96) при смене статуса только логирует, **без** cancel_order_and_release_stock.  
- Bulk «Перевести в Подтверждён» (ction_set_status_confirmed) также не проходит единый сервисный путь побочных эффектов.  
- Статус: подтверждено кодом; идентификатор проблемы остаётся **FUNC-002 / SEC-003**.

#### Прочие подтверждения агентов (уже отражены в B3)

- Expire unpaid без YK pre-sync → **FUNC-001** — подтверждено.  
- Cart clear по product_id → **FUNC-004** — подтверждено.  
- Нет cancel на orders/[id] → **FUNC-005** — подтверждено.  
- Promo stub / bonus spend не в checkout → **FUNC-006 / FUNC-007** — подтверждено.  
- FE не очищает корзину до PAID; return invalidate только при paid — согласовано с B3 §6–7.

### Метаданные завершения Блока № 3

- **Дата:** 2026-11-05  
- **Статус:** завершён (статический)  
- **Проверенные файлы (основные):** orders/cart/payments/products/content/bonus views&services; onec/orders.py; checkout/return/orders FE pages; useCart; auth login; ProfileContent; admin orders; eligibility; checkout_clear; expire/reconcile  
- **Ключевых сценариев в карте:** 11 (S1–S11) + детализация подсценариев каталога/корзины/checkout/pay  
- **Проблемы:** High 3 · Medium 5 · Low 2 · Critical 0  
- **Непроверенные:** §21  
- **Ограничения:** без изменения данных, без внешних API, без запуска тестов с side effects  
- **Подтверждение:** код/конфиги/БД/Git state не изменялись; изменён только docs/audit/RINGO_FULL_AUDIT.md  
- **Подтверждение накопления:** Блоки № 1 и № 2 сохранены без перезаписи; Блок № 3 добавлен в конец файла
---

# БЛОК №4. ТЕХНИЧЕСКОЕ КАЧЕСТВО, АРХИТЕКТУРА, ПРОИЗВОДИТЕЛЬНОСТЬ И СОПРОВОЖДАЕМОСТЬ

**Дата аудита:** 2026-11-05  
**Проверенная ревизия (Git HEAD):** `8a0bd5f` на ветке `main` (working tree dirty; незакоммиченные изменения **не** трогались)  
**Статус блока:** завершён (статический анализ; без runtime-нагрузки, без apply migrations, без внешних вызовов)  
**Режим:** READ-ONLY; изменён только этот накопительный файл.

## 6.1. Общий результат

### Проверенные каталоги / артефакты

- `backend/apps/*`, `backend/integrations/*`, `backend/config/settings/*`, `backend/requirements.txt`, `backend/uv.lock`
- `frontend/src/{app,components,lib}`, `frontend/package.json`, `frontend/package-lock.json`
- `docker-compose.yml` (+ упоминание prod overlay), `docs/` (наличие, не правка)
- Git: `git status` / `rev-parse` (только чтение)

### Выполненные проверки

- Архитектура BE/FE, размер модулей, сервисные границы
- ORM prefetch/select_related на каталоге/заказах
- Celery task patterns, Beat schedule (из кода)
- Compose healthchecks / depends_on / volumes
- Зависимости pinning, тестовая карта (inventory), logging/Sentry hooks
- Сопоставление с SEC/FUNC предыдущих блоков

### Не выполнено (ограничения)

- Lighthouse / Web Vitals / bundle analyzer numbers
- `EXPLAIN` SQL / prod Redis queue depth
- Запуск pytest/vitest (риск изменения test DB / side effects)
- Реальные замеры latency API
- Security advisories по CVE пакетов

---

## 6.2. Сводка находок Блока №4

| Приоритет | Количество |
|---|---:|
| CRITICAL | 0 |
| HIGH | 4 |
| MEDIUM | 8 |
| LOW | 5 |
| INFO | 3 |

**Всего новых TECH-ID:** 22 (`TECH-001` … `TECH-022`)  

| Статус подтверждения | Кол-во |
|---|---:|
| подтверждено кодом | 15 |
| потенциальный риск | 6 |
| требует runtime-проверки | 1 |

---

## 6.3. Архитектурная оценка по областям

| Область | Состояние | Сильные стороны | Слабые стороны / риски |
|---|---|---|---|
| Backend | Рабочая доменная нарезка apps | Отдельные apps, payments eligibility, onec package | God-modules; несколько путей cancel/pay |
| Frontend | App Router + services/hooks | API services слой, dynamic import на home/maps | Много `"use client"`; тяжёлые UI-либы на карточках |
| API | DRF + единый `/api/v1` | Throttles, serializers, OpenAPI optional | FE/BE расхождения контракта (color) — см. FUNC-011 |
| Database | Модели + индексы на заказах/платежах | Prefetch на каталоге; unique paid constraint | Seed RunPython; цвет не в OrderItem |
| Celery/Redis | Beat+Worker в compose | 1C retry/backoff; email idempotency | Payment tasks без time_limit/lock; expire↔YK (FUNC-001) |
| Интеграции | onec/yookassa/sber изолированы | defusedxml, claim sync, timeouts | Два PSP-стека усложняют сопровождение |
| Docker | Compose local + prod overlay | Healthchecks web/db/redis/frontend | Frontend build-on-start; celery depends_on без healthy |
| Testing | Хороший security/payment набор | yookassa/sber/cart retention/onec tests | Дыры: expire YK, admin cancel release, color order |
| Logging/Monitoring | Sentry optional + LOGGING prod | mask PII на login; payment logs без секретов | Нет единого request-id correlation в коде |
| Documentation | Обширный `docs/` | payments/1C/ops | Риск рассинхрона с dirty tree / бонусы/promo |

---

## 6.4. Реестр проблем TECH-XXX

### TECH-001 — Разрозненные пути отмены заказа (архитектурный корень SEC-003 / FUNC-002)

- **Приоритет:** HIGH  
- **Категория:** Backend architecture / domain consistency  
- **Статус:** подтверждено кодом  
- **Пути:** `apps/orders/services/__init__.py` (`cancel_order_and_release_stock`); `apps/orders/views.py` OrderCancelView; `apps/admin_api/views/orders.py` OrderAdminUpdateView; `apps/orders/admin.py` save_model  
- **Обнаружено:** единый сервис cancel+release используется customer API; admin_api и Django Admin меняют `status` напрямую.  
- **Почему проблема:** нарушение single write-path → расхождение побочных эффектов (склад/1С).  
- **Последствия:** «залипший» reserved; рассинхрон 1С.  
- **Условия:** отмена через админку.  
- **Направление исправления:** один domain service для всех UI; admin вызывает его.  
- **Сложность:** средняя  
- **Связь:** **SEC-003**, **FUNC-002**, усиление B3.1  

### TECH-002 — Двойной платёжный стек без полного паритета фоновых путей (корень FUNC-001)

- **Приоритет:** HIGH  
- **Категория:** Backend architecture / payments  
- **Статус:** подтверждено кодом  
- **Пути:** `apps/payments/services.py` (~32 KB, Sber+expire); `apps/payments/yookassa_service.py`; `expire_unpaid_online_orders` sync filter по `sber_order_id`  
- **Обнаружено:** YK вынесен в отдельный модуль, но периодический expire остался Sber-centric; reconcile уже умеет оба.  
- **Почему:** эволюция «Сбер → ЮKassa» без полной унификации scheduled jobs.  
- **Последствия:** гонки late-payment / отмена оплаченного.  
- **Направление:** общий `sync_payment_status` в expire; постепенно facade provider.  
- **Сложность:** средняя  
- **Связь:** **FUNC-001**  

### TECH-003 — Доменная модель заказа без цвета (корень FUNC-011 / усиливает FUNC-003/004)

- **Приоритет:** HIGH  
- **Категория:** Data model / API contract  
- **Статус:** подтверждено кодом  
- **Пути:** `apps/orders/models.py` OrderItem (нет color); FE `checkout/page.tsx` items без color; cart имеет color  
- **Обнаружено:** цвет существует в корзине/каталоге, но не в заказе.  
- **Почему:** неполный aggregate root Order.  
- **Последствия:** комплектация, цена цвета, clear корзины, 1С series ambiguity.  
- **Направление:** поле/snapshot на OrderItem + контракт FE.  
- **Сложность:** средняя–высокая (миграции + FE + возможно 1С)  
- **Связь:** **FUNC-011**, **FUNC-003**, **FUNC-004**  

### TECH-004 — Крупные «god-modules» в критичных доменах

- **Приоритет:** HIGH  
- **Категория:** Maintainability  
- **Статус:** подтверждено кодом (размеры файлов)  
- **Пути:** `integrations/onec/orders.py` (~36 KB); `apps/payments/services.py` (~32 KB); `integrations/onec/importer.py` (~31 KB); `apps/users/views.py` (~27 KB); `apps/orders/views.py` (~26 KB)  
- **Обнаружено:** концентрация reserve/sync/HTTP/policy в единых файлах.  
- **Почему:** повышает стоимость изменений и риск регрессий (как TECH-001/002).  
- **Последствия:** сложнее review/test; выше шанс пропустить ветку провайдера.  
- **Направление:** поэтапное разрезание по use-case (без big-bang rewrite).  
- **Сложность:** высокая  
- **Связь:** TECH-001, TECH-002  

### TECH-005 — Celery payment tasks без time_limit / locking / уникальности

- **Приоритет:** MEDIUM  
- **Категория:** Celery / reliability  
- **Статус:** подтверждено кодом  
- **Пути:** `apps/payments/tasks.py` (`expire_unpaid_online_orders_task`, `reconcile_open_payments_task`) — голые `@shared_task`  
- **Обнаружено:** нет `soft_time_limit`, `acks_late`, distributed lock; Beat каждые 3–5 мин.  
- **Почему:** при медленном PSP/ДБ возможны overlapping runs.  
- **Последствия:** лишняя нагрузка; редкие гонки статусов (select_for_update смягчает paid path).  
- **Направление:** lock key + time limits; мониторинг длительности.  
- **Сложность:** низкая–средняя  
- **Связь:** FUNC-001 (операционный фон)  

### TECH-006 — 1C sync tasks: ручной retry через apply_async вместо autoretry_for

- **Приоритет:** MEDIUM  
- **Категория:** Celery / integrations  
- **Статус:** подтверждено кодом  
- **Пути:** `apps/orders/tasks.py` ~14–96  
- **Обнаружено:** backoff реализован вручную через `_attempt` + `apply_async`; stub mode запрещает nested delay.  
- **Почему:** работает, но нестандартно; сложнее observability (не Celery retry counters).  
- **Последствия:** путаница в ops; при ошибочном stub — нет ретраев.  
- **Направление:** документировать или перейти на `autoretry_for` + claim уже в onec.  
- **Сложность:** средняя  
- **Примечание:** claim/идемпотентность в `integrations/onec/orders.py` — сильная сторона (не ломать).  

### TECH-007 — Product list: prefetch stock без store; detail stock делает select_related на relation

- **Приоритет:** MEDIUM  
- **Категория:** ORM / performance (потенциал)  
- **Статус:** потенциальный риск  
- **Пути:** `products/views.py` ProductListView prefetch `"stock_items"`; `products/serializers.py` get_stock ~248–251 `select_related("store")`  
- **Обнаружено:** list суммирует available без store (OK); detail может инициировать доп. запросы.  
- **Почему:** при росте складов/товаров — лишние SQL.  
- **Условия:** высокие каталожные нагрузки / detail без тёплого cache.  
- **Направление:** Prefetch(..., queryset=Stock.objects.select_related("store")).  
- **Сложность:** низкая  
- **Статус измерений:** требует runtime EXPLAIN / query count  

### TECH-008 — Кеш полного JSON списка товаров в Redis

- **Приоритет:** MEDIUM  
- **Категория:** Cache / performance  
- **Статус:** подтверждено кодом  
- **Пути:** `products/views.py` list/detail cache.set response.data  
- **Обнаружено:** кешируется готовый DRF payload по ключу фильтров.  
- **Почему:** плюс для read; риск больших значений и stale при промахе invalidation.  
- **Последствия:** память Redis; редкий stale если signal не покрыл путь.  
- **Направление:** мониторинг hit/size; короткий TTL уже есть через settings.  
- **Сложность:** низкая  
- **Связь:** signals invalidation — положительный паттерн  

### TECH-009 — Frontend: высокая доля Client Components + тяжёлые UI-библиотеки на витрине

- **Приоритет:** MEDIUM  
- **Категория:** Frontend performance / bundle  
- **Статус:** потенциальный риск (без bundle report)  
- **Пути:** ~100+ файлов с `"use client"`; `ProductCard.tsx` тянет swiper+framer-motion; `three`/`@react-three/*` в deps; `ModelViewer.tsx` placeholder Canvas  
- **Обнаружено:** home использует `dynamic()` (хорошо); карточки товаров синхронно грузят Swiper/motion.  
- **Почему:** увеличивает JS на каталоге.  
- **Условия:** мобильный LCP/INP при длинной выдаче.  
- **Направление:** lazy swiper; tree-shake 3D только на PDP с флагом; замер `npm run analyze`.  
- **Сложность:** средняя  

### TECH-010 — Compose: frontend production-start с bind-mount и build при отсутствии BUILD_ID

- **Приоритет:** MEDIUM  
- **Категория:** Docker / DX / reproducibility  
- **Статус:** подтверждено кодом  
- **Пути:** `docker-compose.yml` service `frontend` command ~148–161; volumes `./frontend:/app`  
- **Обнаружено:** `NODE_ENV=production` + иногда `npm run build` внутри start; health start_period 600s.  
- **Почему:** непредсказуемое время старта; смешение dev mount и prod server.  
- **Последствия:** флаки локального стенда; долгий cold start.  
- **Направление:** разделить Dockerfile.dev / prod image с заранее собранным `.next`.  
- **Сложность:** средняя  

### TECH-011 — Celery services: depends_on без wait-for-healthy DB (в отличие от web)

- **Приоритет:** MEDIUM  
- **Категория:** Docker / startup races  
- **Статус:** потенциальный риск  
- **Пути:** `docker-compose.yml` celery/celery-beat depends_on db/redis/web без `condition: service_healthy`  
- **Почему:** worker может стартовать раньше готовности Postgres.  
- **Последствия:** стартовые ошибки задач до reconnect.  
- **Направление:** condition healthy + retry.  
- **Сложность:** низкая  

### TECH-012 — Backend зависимости: ranges в requirements.txt при наличии uv.lock

- **Приоритет:** MEDIUM  
- **Категория:** Dependencies / supply chain  
- **Статус:** подтверждено кодом  
- **Пути:** `backend/requirements.txt` (`Django>=5.0,<6.0` и др.); `backend/uv.lock` существует  
- **Обнаружено:** воспроизводимость зависит от того, используется ли lock в Docker build.  
- **Почему:** разные машины → разные минорные версии.  
- **Направление:** единый путь install из lock в Dockerfile; CI pin check.  
- **Сложность:** низкая–средняя  

### TECH-013 — Bonus app: живые signals при отключённом API (архитектурный долг)

- **Приоритет:** LOW  
- **Категория:** Feature flags / consistency  
- **Статус:** подтверждено кодом  
- **Пути:** `apps/bonus/apps.py` ready(); `config/api_urls.py` bonus commented  
- **Связь:** **FUNC-007**  
- **Направление:** единый feature flag на signals+API+UI.  
- **Сложность:** низкая  

### TECH-014 — Промокоды: validate API без write-path в Order (контрактный долг)

- **Приоритет:** LOW  
- **Категория:** API completeness  
- **Статус:** подтверждено кодом  
- **Связь:** **FUNC-006**  
- **Направление:** либо apply в OrderCreate, либо не экспонировать как «готово».  
- **Сложность:** средняя  

### TECH-015 — Staff access dual-model (customer orders vs admin_api)

- **Приоритет:** MEDIUM (техдолг доступа; security уже SEC-001)  
- **Категория:** Authorization architecture  
- **Статус:** подтверждено кодом  
- **Связь:** **SEC-001**, **FUNC-010**  
- **Техническая причина:** `is_staff` shortcut в customer queryset vs RBAC+MFA в admin_api.  
- **Направление:** убрать staff bypass из customer API.  
- **Сложность:** средняя  

### TECH-016 — Тестовые пробелы на известных FUNC/SEC регрессиях

- **Приоритет:** MEDIUM  
- **Категория:** Testing  
- **Статус:** подтверждено инвентаризацией тестов (без запуска)  
- **Пути:** `backend/tests/` — есть yookassa/sber/cart retention/repay; **не видно** явных тестов: expire+YK pre-sync, admin cancel→release, OrderItem color  
- **Почему:** регрессии TECH-001/002/003 могут вернуться.  
- **Направление:** добавить targeted tests после фиксов.  
- **Сложность:** низкая–средняя  

### TECH-017 — Stores seed RunPython в миграциях

- **Приоритет:** LOW  
- **Категория:** Migrations / deploy  
- **Статус:** подтверждено кодом  
- **Пути:** `stores/migrations/0003_seed_stores_and_managers.py`, `0004_...` RunPython  
- **Почему:** свежая БД получает seed-данные; prod migrate тащит контент.  
- **Направление:** data migration → management command.  
- **Сложность:** средняя  

### TECH-018 — optional_task stub: sync execution без очереди

- **Приоритет:** LOW  
- **Категория:** Deploy variants (Vercel)  
- **Статус:** подтверждено кодом  
- **Пути:** `config/optional_task.py`  
- **Почему:** на окружении без Celery `.delay` выполняется inline — latency UX и иные retry semantics.  
- **Направление:** явно документировать/алертить stub mode.  
- **Сложность:** низкая  

### TECH-019 — TypeScript `any` / слабые типы в maps/tests

- **Приоритет:** LOW  
- **Категория:** Frontend typing  
- **Статус:** подтверждено кодом (точечно)  
- **Пути:** `YandexMap.tsx` `ymaps?: any`; тесты `as any`  
- **Почему:** локально снижает безопасность рефакторинга карт.  
- **Направление:** минимальные типы ymaps / тестовые фабрики.  
- **Сложность:** низкая  

### TECH-020 — Observability: нет сквозного request/correlation id в API↔Celery

- **Приоритет:** INFO  
- **Категория:** Logging / ops  
- **Статус:** потенциальный риск / наблюдение  
- **Обнаружено:** Sentry init в base; LOGGING в production; payment/1C логируют order_id — хорошо; единого middleware correlation id не найдено.  
- **Направление:** request id → logs → Celery headers.  
- **Сложность:** средняя  

### TECH-021 — admin_api без классического AppConfig/models

- **Приоритет:** INFO  
- **Категория:** Project structure  
- **Статус:** подтверждено (B1)  
- **Почему:** работает как views package; новичкам неочевидно.  
- **Направление:** документировать или оформить AppConfig.  
- **Сложность:** низкая  

### TECH-022 — Документация vs dirty tree / feature flags

- **Приоритет:** INFO  
- **Категория:** Documentation drift  
- **Статус:** потенциальный риск  
- **Обнаружено:** большой `docs/` + незакоммиченные изменения (YooKassa/cart/security).  
- **Почему:** onboarding может читать устаревшие Sber-first инструкции.  
- **Направление:** после стабилизации — сверка docs/payments и 1C.  
- **Сложность:** средняя  

---

## 6.5. Что сделано правильно (не переписывать без причины)

1. Разделение Django apps по доменам + `integrations/*` для внешних систем.  
2. Серверный пересчёт цен заказа; eligibility оплаты; unique paid constraint.  
3. Online cart retention + clear after PAID (продуктовое правило).  
4. Prefetch/select_related на каталоге; cache + signals invalidation.  
5. 1C: defusedxml, base URL normalize, sync claim, HTTP вне long locks, retryable errors.  
6. YooKassa paid только после trusted GET + amount/metadata.  
7. FE: слой `lib/api/services`, TanStack Query, dynamic import maps/home sections.  
8. Production settings fail-closed; optional Sentry scrubbing.  
9. Набор backend tests по платежам/1С/cart retention/security.  
10. Compose healthchecks для db/redis/web/frontend.

---

## 6.6. Что проверить отдельно (runtime)

1. Bundle size / LCP каталога с ProductCard (Swiper+motion).  
2. Query count ProductDetail при cold cache.  
3. Redis memory от product list cache keys.  
4. Overlap expire/reconcile под latency ЮKassa.  
5. Startup race celery vs Postgres на чистом `compose up`.  
6. Фактическое использование `uv.lock` в Docker build CI/CD.  
7. Web Vitals на `ringoo15.store`.  
8. Покрытие тестами после фиксов FUNC-001/002/011.

---

## 6.7. Предварительный план технических улучшений (без реализации)

### Необходимые

1. Единый cancel domain path (TECH-001 / SEC-003 / FUNC-002).  
2. Expire unpaid: sync YooKassa (TECH-002 / FUNC-001).  
3. Модель/контракт цвета в заказе (TECH-003 / FUNC-011).  
4. Выровнять staff access customer vs admin_api (TECH-015 / SEC-001).  

### Желательные

5. time_limit/lock на payment beat tasks (TECH-005).  
6. Prefetch Stock+store (TECH-007).  
7. Compose frontend/prod split + celery healthy depends (TECH-010/011).  
8. Lockfile-enforced backend installs (TECH-012).  
9. Тесты на expire YK / admin cancel (TECH-016).  

### На перспективу

10. Распил god-modules (TECH-004).  
11. FE bundle hygiene каталога (TECH-009).  
12. Correlation IDs (TECH-020).  
13. Вынести seed из миграций (TECH-017).  

### Пока нецелесообразно

- Полный rewrite Frontend state management.  
- Смена ORM/фреймворка.  
- Удаление Сбер-кода до продуктового решения (лучше facade + flags).  
- Массовый перевод всех страниц на RSC без замеров.

---

## 7. Сопоставление с предыдущими блоками

| Ранее | Техническая связь в B4 |
|---|---|
| SEC-001 / FUNC-010 | TECH-015 — два слоя авторизации staff |
| SEC-003 / FUNC-002 | TECH-001 — нет единого cancel write-path (+ Django Admin) |
| FUNC-001 | TECH-002 / TECH-005 — неполный паритет YK в scheduled jobs |
| FUNC-004 | TECH-003 — clear по product_id логичен при отсутствии color на заказе |
| FUNC-006 | TECH-014 — validate без order apply |
| FUNC-007 | TECH-013 — signals без API |
| FUNC-011 | TECH-003 — отсутствие color в домене Order |
| FUNC-003 | TECH-003 / цена цвета vs Product.price |

Старые ID **не переименовывались** и **не удалялись**.

---

### Метаданные завершения Блока №4

- **Дата:** 2026-11-05  
- **Статус:** завершён (статический)  
- **Новых TECH:** 22 (CRITICAL 0 · HIGH 4 · MEDIUM 8 · LOW 5 · INFO 3)  
- **Инструменты:** чтение кода, grep, размеры файлов, git status (RO)  
- **Подтверждение:** исходники/конфиги/БД/Docker/Git **не изменялись**; добавлен только раздел в `docs/audit/RINGO_FULL_AUDIT.md`  
- **Подтверждение накопления:** Блоки №1–3 и уточнение B3.1 сохранены; Блок №4 добавлен в конец файла

---

# БЛОК №5. АУДИТ ЭКСПЛУАТАЦИОННОЙ ГОТОВНОСТИ RINGO (PRODUCTION READINESS)

**Дата:** 2026-11-05  
**Режим:** READ-ONLY (кроме append в этот файл)  
**Область:** развёртывание, env/prod, HTTPS/сеть, backup/DR, обновления, устойчивость, мониторинг, ops платежей/1С, Media, операционная документация  
**Предыдущие блоки:** №1–№4 + уточнение B3.1 сохранены без изменений ID  
**Git (RO):** ветка main, HEAD 8a0bd5f, dirty working tree (~238 porcelain entries)  
**Ограничения:** DNS/TLS/firewall на живом VPS, реальный cron/offsite, restore drill, реальные платежи и изменяющие вызовы 1С — **не выполнялись**

---

## 5.1. Ответы на ключевые вопросы

| # | Вопрос | Ответ |
|---|---|---|
| 1 | Можно ли развернуть без ручных исправлений и непредусмотренных действий? | **Нет.** Нужны ручные шаги: .env.production, Compose ≥2.24, dual-file compose, роль PG, MFA, Caddy/firewall, migrate/collectstatic. Часть docs расходится (docs/DEPLOYMENT.md vs checklist). |
| 2 | Можно ли безопасно запустить для реальных пользователей? | **С условиями:** публичный demo / заказы без онлайн-оплаты — после P0 ops. Полный коммерческий запуск с ЮKassa/1С — **нет**, пока не закрыты SEC/FUNC P0 и не подтверждены backup/мониторинг. |
| 3 | Можно ли обнаружить и диагностировать отказ? | **Частично:** есть /health/ (DB+cache), Docker healthchecks, логи volumes. Нет подтверждённого внешнего uptime, алертов Celery/диска/5xx, очереди задач. |
| 4 | Можно ли восстановить после серьёзного сбоя? | **Процедуры описаны, исполнение не подтверждено.** Скрипты dump/restore есть; offsite + cron + restore drill = **NOT VERIFIED**. Media отдельно от PG. |
| 5 | Можно ли безопасно обновлять приложение? | **Частично вручную:** checklist есть; нет CD, нет обязательного pre-migrate backup gate в автоматике, rollback образов не формализован. |
| 6 | Можно ли поддерживать магазин без постоянного разработчика? | **Ограниченно** для soft-launch при заполненных runbook. Инциденты платежей/1С/миграций/споров потребуют разработчика. |
| 7 | Какие эксплуатационные риски устранить до запуска? | См. P0: offsite+cron+drill backup, 
estart policy, воспроизводимый deploy-артефакт, TLS/firewall verify, мониторинг минимума, не включать online pay/1С. |

---

## 5.2. Готовность компонентов

| Компонент | Статус | Основание |
|---|---|---|
| Backend (Gunicorn/Django prod) | READY WITH CONDITIONS | docker-compose.prod.yml + config.settings.production fail-closed; migrate/collectstatic вручную; dirty tree |
| Frontend (Next prod) | READY WITH CONDITIONS | prod image + NEXT_PUBLIC_* build args; proxy к web; online pay flag default 0 |
| PostgreSQL | READY WITH CONDITIONS | volumes, healthcheck, ports reset в prod; least-privilege docs; backup drill не подтверждён |
| Redis | READY WITH CONDITIONS | password required в prod overlay; AOF; ports закрыты в overlay |
| Celery Worker | READY WITH CONDITIONS | сервис в compose; resource limits; нет restart policy; нет алерта очереди |
| Celery Beat | READY WITH CONDITIONS | сервис есть; schedule expire; зависит от worker; без мониторинга остановки |
| ЮKassa | NOT READY (для live) / READY WITH CONDITIONS (выкл.) | default YOOKASSA_ENABLED=0, TEST_MODE=1; live блокируется FUNC-001 и ops пробелами |
| Сбер | NOT READY (gated off) | SBER_ECOM_ENABLED=false в prod example; сохранённый код не для текущего go-live |
| 1С | NOT READY (для постоянной работы) | flags off; site≠1С server корректно; ops journal/retry для prod не подтверждены как runbook для оператора |
| Reverse proxy / TLS | NOT VERIFIED (живо) / READY WITH CONDITIONS (артефакты) | Caddy 
ingoo15.store example; живой TLS/DNS не проверялись |
| Backup automation | NOT READY | скрипты есть; cron/offsite/drill не подтверждены в окружении |
| Monitoring/alerting | NOT READY | health endpoint есть; внешней системы алертов в репо нет |

---

## 5.3. Развёртывание на сервере

**Что подтверждено конфигурацией/документацией:**

- Целевой путь: docs/PRODUCTION_DEPLOYMENT_CHECKLIST.md, docs/FINAL_DEPLOYMENT_CHECKLIST.md (public demo без online pay/1С).
- Compose: docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production.
- Требование Compose ≥ 2.24 (!override, ports: !reset []).
- Подготовка сервера, ufw, Caddy/Nginx examples: docs/ops/VPS_FIREWALL_AND_TLS.md, docs/ops/caddy.ringoo15.store.caddyfile.
- После старта: check --deploy, migrate, collectstatic, createsuperuser, MFA (docs/ops/ADMIN_MFA_SETUP.md).
- Архитектура: сайт на отдельном VPS; 1С снаружи; сайт — HTTP-клиент 1С (не размещение на сервере 1С).

**Что отсутствует / риск:**

- Живой VPS/DNS/TLS/firewall — **NOT VERIFIED** (read-only, без сетевых изменений).
- docs/DEPLOYMENT.md частично устарел (одиночный docker-compose.prod.yml build, DB_USER=postgres, путь ackend/.env) — риск ошибочного запуска.
- Нет CD workflow (только CI; lighthouse cron). Deploy = ручной git + compose на VPS.
- Рабочее дерево локально грязное → деплой «как есть» ≠ origin/main HEAD.

**Вывод по развёртыванию:** воспроизводимый сценарий **есть** в checklist’ах; без строгого следования актуальному checklist и без чистого tagged release — высокий риск ручных ошибок.

---

## 5.4. Переменные окружения и конфигурация

**Артефакты:** .env.production.example, .env.example, ackend/.env.example, .env.backup.example, prod compose required vars (SECRET_KEY, DATABASE_URL, REDIS_URL, ALLOWED_HOSTS, CORS/CSRF, NEXT_PUBLIC_*).

**Подтверждено:**

- Prod settings fail-closed: DEBUG запрещён; SECRET_KEY/ALLOWED_HOSTS/OTP/DB/Redis обязательны (ackend/config/settings/production.py).
- При YOOKASSA_ENABLED — проверка shop/secret и согласования test_/live ключей с YOOKASSA_TEST_MODE.
- Публичные NEXT_PUBLIC_* отделены от серверных секретов ЮKassa.
- Soft-launch defaults: online pay / Sber / 1С выключены.

**Риски:**

- Несколько мест env (./.env.production, ./backend/.env.production, optional) — оператор может заполнить не тот файл.
- DEPLOYMENT.md рекомендует устаревшие значения → конфликт с least-privilege.
- Значения локального .env **не анализировались на содержимое** (секреты); наличие файла не равно корректности prod.

**Поведение при неполной конфигурации:** production модуль поднимает ImproperlyConfigured на критичных пропусках — хорошо. Dev compose со слабыми default паролями **нельзя** путать с prod.

---

## 5.5. Домен, HTTPS и сетевой контур

| Элемент | Статус |
|---|---|
| Домен 
ingoo15.store в example env + Caddyfile | подготовлено в репо |
| Frontend → API proxy (RINGOO_API_PROXY_TARGET / internal URL) | в prod compose |
| Publish только 127.0.0.1:3000/8000 | в prod overlay |
| DB/Redis без published ports | ports: !reset [] |
| HTTP→HTTPS / LE | через Caddy (описано); **живо NOT VERIFIED** |
| TRUST_PROXY / Axes proxy count | в example |
| Изоляция от сервера 1С | корректная модель «сайт клиент 1С» |
| Ограничение тестовой среды без блокировки 1С | возможно firewall/ACL на VPS; **не верифицировано на сервере** |

DNS-запросы и изменения сети **не выполнялись**.

---

## 5.6. Резервное копирование PostgreSQL

| Аспект | Факт |
|---|---|
| Скрипты | scripts/backup-db.sh, ackup-media.sh, ackup-all.sh, ackup-db-encrypted.sh |
| Restore | scripts/restore-db.sh, 
estore-media.sh |
| Docs | docs/BACKUP.md, docs/ops/BACKUP_AND_RESTORE.md |
| Формат | pg_dump → gzip (plain SQL stream); encrypted variant via ge |
| Хранение по умолчанию | ./backups **на том же хосте/проекте** |
| Ротация | BACKUP_KEEP_DAYS default 7 в ackup-all.sh |
| Offsite | **явно NOT VERIFIED** в docs; S3 не автоматизирован |
| Cron в репо | только инструкция; **нет** unit/compose cron-сервиса с подтверждённой установкой |
| Целостность архивов | нет автоматической gzip -t / checksum gate |
| Уведомления об ошибке backup | отсутствуют |
| Restore drill | описан; выполнение на отдельной среде **NOT VERIFIED** |
| Риск потери всех копий при отказе VPS | **да**, пока только local backups |
| PG dump достаточен для полного магазина? | **нет** — нужны Media (+ код/env/секреты offline) |

**Вердикт Backup:** механизм **подготовлен кодом**, эксплуатационно **NOT READY** до cron + encryption + offsite + успешного restore drill.

---

## 5.7. Disaster Recovery (сценарии)

RPO/RTO в docs — **рекомендации** (≤24h / ≤4h). **Утверждённых владельцем значений нет** — не выдуманы.

| Сценарий | Недоступность / потеря | Восстановление | Документация | Остаточный риск |
|---|---|---|---|---|
| Полная потеря VPS | весь сайт | новый VPS + restore DB/Media + env/Caddy | частично | без offsite — **потеря данных** |
| Повреждение PostgreSQL | заказы/каталог/пользователи | 
estore-db.sh | да | без свежего dump — потеря с last backup |
| Случайное удаление данных | строки/таблицы | restore / point-in-time **нет** (только full dump) | dump only | RPO = интервал backup |
| Потеря Redis | сессии cache, idempotency, Celery broker | пересоздание Redis; задачи в полёте теряются | слабо | дубли заказов при LocMem — в prod должен быть Redis |
| Повреждение Media | картинки товаров | 
estore-media.sh | да | без media backup — витрина «пустая» |
| Отказ Backend/Frontend | витрина/API | recreate containers | checklist | без 
estart — после reboot могут не подняться |
| Остановка Celery Worker/Beat | sync/expire/email jobs | ручной restart | слабо | FUNC-001 expire без beat |
| Потеря связи с 1С | нет sync остатков/заказов | сайт может жить; расхождение склада | частично | ручная сверка |
| Недоступность ЮKassa | online pay | при soft-launch offline — ок | pay docs | зависания pending при live |
| Истечение SSL | HTTPS down | Caddy renew / ручной LE | ops TLS | без мониторинга cert — простой |
| Потеря .env.production | невозможность корректного recreate | из secret store / offline copy | не формализовано | **критично** хранить offline |

---

## 5.8. Обновления и миграции

- Инструкции: checklist + Makefile/compose rebuild; migrate вручную после backup.
- Нет automated blue/green / rolling с проверкой совместимости схемы.
- Риск одновременной работы old/new workers при breaking migration — **не закрыт** оркестрацией (нужна ручная остановка web/celery → migrate → up).
- Несовместимые миграции + dirty tree (новые migration files untracked) — деплой с незакоммиченными миграциями опасен.
- Откат приложения: предыдущий image tag **не закреплён** политикой в docs как обязательный артефакт.

**Безопасный выпуск без потери заказов/платежей:** возможен только при pre-backup, short maintenance window, и при выключенных online payments. При live ЮKassa — дополнительно риск FUNC-001.

---

## 5.9. Доступность и устойчивость

| Механизм | Факт в репо |
|---|---|
| 
estart: policy | **отсутствует** во всех docker-compose*.yml |
| Healthchecks | db/redis/web (и др. в base) — есть |
| depends_on healthy | web/celery ждут db/redis |
| Resource limits | в prod overlay (cpus/memory) |
| Поведение после reboot VPS | контейнеры **могут не стартовать** без restart policy / systemd |
| Disk full / log growth | logs volume без ротации в compose; риск заполнения диска |
| Celery queue backlog | нет метрик/алертов |
| Внешние API temporary fail | код ретраев в интеграциях — см. B3/B4; ops алерт нет |

Не утверждается автовосстановление сервисов после reboot — конфигурация этого **не подтверждает**.

---

## 5.10. Мониторинг и уведомления

**Есть:**

- GET /health/ — DB + cache, без утечки exception text (ackend/config/views.py).
- Docker healthcheck web → /health/.
- Optional Sentry (SENTRY_DSN).
- LOGGING в production; volumes логов.

**Нет подтверждённого:**

- Uptime check сайта/API с уведомлением оператору.
- Алерт остановки Celery worker/beat, роста очереди.
- Алерт заполнения диска, ошибок backup, истечения TLS.
- Централизованный dashboard 5xx / latency (кроме optional Sentry).
- Алерт ошибок платежей / 1С sync.

**Кто получает уведомления:** в репозитории канал on-call **не зафиксирован**.

---

## 5.11. Эксплуатация платежей

Для **текущего go-live профиля** (online off): эксплуатационно приемлемо при скрытом UI flag.

Для **включения ЮKassa live** ops-готовность **недостаточна**:

- Test/live разделение в settings есть.
- Webhook/repay код есть (B2/B3), но FUNC-001 (expire без YK sync) — операционный риск ложных cancel.
- Нет runbook оператора «зависший pending / спор / возврат» как единой короткой инструкции для non-dev (частично размазано по docs/payments/*).
- Мониторинг незавершённых платежей не автоматизирован.
- Сбер сохранён, но gated — не путать с активным провайдером.

---

## 5.12. Эксплуатация 1С

- Подключение документировано в интеграционных docs; flags default off.
- Site и 1С на разных серверах — соответствует требованию.
- Проверка соединения / журнал / retry — на уровне кода/задач частично; **операторский** runbook «что делать при частичной синхронизации» для non-dev — слабый.
- Обнаружение «давно не было успешного sync» — без алерта.
- Включать write-sync до закрытия складских FUNC/SEC рисков **нельзя**.

---

## 5.13. Media и файлы

- media_volume / static_volume в prod (без bind ./backend).
- Backup/restore media scripts существуют.
- PG backup **не** восстанавливает изображения.
- Рост диска media+backups+logs — без квот/алертов.
- Имя volume по умолчанию 
ingoo_media_volume — зависит от compose project name.

---

## 5.14. Операционная готовность команды (non-developer)

| Действие | Документация |
|---|---|
| Первый запуск | FINAL/PRODUCTION checklists — **есть** (нужна дисциплина выбора актуального docs) |
| Состояние системы | health + docker compose ps — частично |
| Логи | docker logs / volume — базово |
| Перезапуск сервиса | стандарт docker — не выделен runbook |
| Celery/Redis/PG checks | фрагментарно |
| Платежи / 1С | для soft-launch «выкл»; live — сложно |
| Backup/restore | docs есть; практика не подтверждена |
| Update | checklist; нет CD |
| Incident / контакт разработчика | **не формализован** escalation path |

---

## 5.15. Обязательные эксплуатационные сценарии

| Сценарий | Подготовленность | Что подтверждено | Что отсутствует | Риск |
|---|---|---|---|---|
| 1. Развёртывание на чистом VPS | Частичная | Checklists, compose prod, env example | Живой прогон; риск устаревшего DEPLOYMENT.md | HIGH |
| 2. Перезапуск VPS после аварии | Слабая | Volumes сохраняют данные | Нет 
estart: policy | CRITICAL |
| 3. Перезапуск PostgreSQL | Средняя | healthcheck; depends_on | ручной контроль приложений | MEDIUM |
| 4. Перезапуск Redis | Средняя | healthcheck; AOF | потеря очереди Celery in-flight | MEDIUM |
| 5. Перезапуск Backend | Средняя | healthcheck web | без restart auto | MEDIUM |
| 6. Перезапуск Frontend | Средняя | depends_on web healthy | без restart auto | MEDIUM |
| 7. Остановка Celery Worker | Слабая | сервис в compose | нет алерта; backlog | HIGH |
| 8. Остановка Celery Beat | Слабая | schedule в settings | expire/jobs встанут (FUNC-001) | HIGH |
| 9. Потеря связи с 1С | Частичная (при выкл. — N/A) | flags off на soft-launch | нет алерта sync lag | MEDIUM при включении |
| 10. Недоступность ЮKassa | OK при offline | flags/UI off | при live — зависания/споры | HIGH при включении |
| 11. Неудачное обновление | Слабая | ручной migrate | нет auto rollback / image pin policy | HIGH |
| 12. Restore PostgreSQL | Частичная | scripts + docs | drill/offsite NOT VERIFIED; user mismatch risk | CRITICAL |
| 13. Restore Media | Частичная | restore-media.sh | drill; volume name | HIGH |
| 14. Истечение HTTPS | Частичная | Caddy auto-renew описан | нет мониторинга expiry | MEDIUM |
| 15. Заполнение диска | Слабая | — | нет алерта/ротации логов в compose | HIGH |
| 16. Много ошибок API | Слабая | optional Sentry; logs | нет on-call алерта 5xx | HIGH |

---

## 5.16. Находки OPS-*

### OPS-001 — Offsite backup, cron и restore drill не подтверждены
- **Приоритет:** CRITICAL  
- **Область:** PostgreSQL Backup / DR  
- **Статус подтверждения:** подтверждено документацией + потенциальный риск; исполнение на сервере — невозможно проверить в read-only  
- **Пути:** scripts/backup-*.sh, docs/ops/BACKUP_AND_RESTORE.md, docs/BACKUP.md, docs/PRODUCTION_DEPLOYMENT_CHECKLIST.md §F  
- **Обнаружено:** скрипты локального dump/media есть; docs сами маркируют offsite как NOT VERIFIED; cron только как инструкция; drill не подтверждён.  
- **Почему важно:** без offsite+расписания+проверки restore возможен **безвозвратный** loss заказов/ПДн при отказе VPS.  
- **Последствия:** простой + потеря данных; невозможность соблюсти заявленный RPO.  
- **Условия:** отказ диска/VPS или «забыли поставить cron».  
- **Устранение:** поставить encrypted daily job, копировать offsite, провести restore drill, зафиксировать результат.  
- **Сложность:** средняя.  
- **Зависимости:** OPS-007, OPS-010.  
- **Связь:** TECH/SEC не дублируют; усиливает риск любых data-loss дефектов B2–B4.

### OPS-002 — Нет Docker 
estart policy
- **Приоритет:** CRITICAL  
- **Область:** Docker и сервисы / Availability  
- **Статус:** подтверждено конфигурацией  
- **Пути:** docker-compose.yml, docker-compose.prod.yml (grep: нет 
estart:)  
- **Обнаружено:** ни один сервис не задаёт 
estart: unless-stopped / lways.  
- **Почему важно:** после reboot/OOM Docker по умолчанию может оставить стек остановленным.  
- **Последствия:** длительный простой витрины/оплаты/Celery без явного сигнала.  
- **Условия:** reboot VPS, падение демона, ручной stop без start.  
- **Устранение:** добавить restart policy (+ ideally systemd/watchdog для compose).  
- **Сложность:** низкая.  
- **Зависимости:** OPS-004 (иначе простой незаметен).  

### OPS-003 — Невоспроизводимый deploy из грязного дерева / отсутствия release tag
- **Приоритет:** HIGH  
- **Область:** Развёртывание / Обновления  
- **Статус:** подтверждено Git status (RO)  
- **Путь:** working tree vs origin/main @ 8a0bd5f (~238 изменений)  
- **Обнаружено:** критичные prod/payment/migration файлы изменены или untracked.  
- **Почему важно:** «что на VPS» ≠ чистый commit; rollback/audit невозможны.  
- **Последствия:** непредсказуемое поведение после обновления; потеря изменений при clone.  
- **Устранение:** зафиксировать release commit/tag; деплоить только артефакт.  
- **Сложность:** средняя (организационно).  
- **Связь:** все незакоммиченные FIX из B2–B4.

### OPS-004 — Нет эксплуатационного мониторинга и алертов
- **Приоритет:** HIGH  
- **Область:** Мониторинг  
- **Статус:** подтверждено отсутствием конфигов; health есть  
- **Пути:** ackend/config/views.py (health_check); нет uptime/alert configs в ops  
- **Обнаружено:** /health/ проверяет DB+cache; нет Celery/queue/disk/TLS/5xx alerting; on-call канал не описан.  
- **Последствия:** отказ обнаруживается клиентами, а не ops.  
- **Устранение:** минимальный uptime (сайт+/health), алерт restart/Celery/disk; optional Sentry с получателем.  
- **Сложность:** средняя.  
- **Связь:** TECH-022 (correlation), FUNC-001 (beat).

### OPS-005 — Полный коммерческий контур (ЮKassa/1С) не готов к эксплуатации
- **Приоритет:** HIGH  
- **Область:** Платежи / 1С  
- **Статус:** подтверждено конфигурацией defaults + связью с FUNC/SEC  
- **Пути:** .env.production.example, docker-compose.prod.yml, docs/FINAL_DEPLOYMENT_CHECKLIST.md  
- **Обнаружено:** soft-launch сознательно выключает online pay/1С; live включение упирается в FUNC-001, SEC-003/FUNC-002, склад/цвет и отсутствие payment ops monitoring.  
- **Последствия:** при преждевременном включении — финансовые/складские инциденты.  
- **Устранение:** держать выкл. до P0 product fixes + ops runbooks + мониторинг pending.  
- **Сложность:** высокая (зависит от B2–B3).  
- **Связь:** FUNC-001, SEC-003, FUNC-002, FUNC-011, SEC-001.

### OPS-006 — Расхождение эксплуатационных инструкций деплоя
- **Приоритет:** MEDIUM  
- **Область:** Эксплуатационная документация  
- **Статус:** подтверждено документацией  
- **Пути:** docs/DEPLOYMENT.md vs docs/PRODUCTION_DEPLOYMENT_CHECKLIST.md / FINAL_DEPLOYMENT_CHECKLIST.md  
- **Обнаружено:** устаревшие команды/compose/env/DB_USER в DEPLOYMENT.md.  
- **Последствия:** ошибочный prod (открытые порты, wrong role, wrong env file).  
- **Устранение:** пометить DEPLOYMENT.md deprecated или синхронизировать; единый source of truth.  
- **Сложность:** низкая.

### OPS-007 — Backup по умолчанию на том же VPS; encrypted path не встроен в backup-all
- **Приоритет:** MEDIUM (CRITICAL в сочетании с OPS-001)  
- **Область:** Backup  
- **Статус:** подтверждено конфигурацией скриптов  
- **Пути:** scripts/backup-all.sh, ackup-db-encrypted.sh  
- **Обнаружено:** ackup-all пишет plaintext gz локально; encrypted — отдельный скрипт.  
- **Последствия:** ransomware/диск/VPS loss уничтожает и данные, и копии.  
- **Устранение:** сделать encrypted+offsite default path.  
- **Сложность:** средняя.

### OPS-008 — Нет CD и формализованного rollback обновлений
- **Приоритет:** MEDIUM  
- **Область:** Обновления  
- **Статус:** подтверждено .github/workflows (нет deploy)  
- **Обнаружено:** только CI/lighthouse; обновление = SSH + compose build; image tags не policy.  
- **Последствия:** длительный/ошибочный rollback после bad migrate.  
- **Устранение:** tagged images + pre-backup checklist gate + documented rollback.  
- **Сложность:** средняя/высокая.

### OPS-009 — Остановка Celery Beat/Worker без обнаружения ломает фон (в т.ч. expire)
- **Приоритет:** MEDIUM  
- **Область:** Celery / Платежи ops  
- **Статус:** подтверждено compose + CELERY_BEAT_SCHEDULE  
- **Пути:** docker-compose.prod.yml celery/celery-beat; ackend/config/settings/base.py CELERY_BEAT_SCHEDULE  
- **Связь:** FUNC-001 — expire job.  
- **Устранение:** health/heartbeat мониторинг Celery; алерт.  
- **Сложность:** средняя.

### OPS-010 — Полное восстановление магазина требует Media + env, не только PG
- **Приоритет:** MEDIUM  
- **Область:** Media / DR  
- **Статус:** подтверждено архитектурой volumes + scripts  
- **Пути:** media_volume, scripts/backup-media.sh, 
estore-media.sh  
- **Обнаружено:** витрина без media backup визуально «мертва»; секреты env не в DB dump.  
- **Устранение:** включать media в обязательный backup set; хранить env offline.  
- **Сложность:** низкая/средняя.

### OPS-011 — Живые DNS / TLS / firewall не верифицированы аудитом
- **Приоритет:** MEDIUM  
- **Область:** Домен и HTTPS  
- **Статус:** невозможно проверить в рамках read-only без влияния; docs = NOT VERIFIED  
- **Пути:** docs/ops/VPS_FIREWALL_AND_TLS.md, docs/ops/caddy.ringoo15.store.caddyfile  
- **Устранение:** внешний port scan + curl -I https://… + cert dates владельцем.  
- **Сложность:** низкая (ops verify).

### OPS-012 — RPO/RTO не утверждены владельцем
- **Приоритет:** LOW  
- **Область:** DR policy  
- **Статус:** подтверждено документацией (рекомендации)  
- **Пути:** docs/ops/BACKUP_AND_RESTORE.md, PRODUCTION checklist  
- **Устранение:** зафиксировать бизнес-значения и подогнать частоту backup.  
- **Сложность:** низкая.

### OPS-013 — Несогласованность default DB_USER в backup vs restore
- **Приоритет:** LOW  
- **Область:** Backup/Restore scripts  
- **Статус:** подтверждено конфигурацией  
- **Пути:** scripts/backup-db.sh (
ingoo_admin), scripts/restore-db.sh (postgres)  
- **Последствия:** restore «из коробки» может падать на prod ролях.  
- **Устранение:** унифицировать defaults с .env.backup.example.  
- **Сложность:** низкая.

### OPS-014 — Примеры Caddy/Nginx и soft-launch checklist подготовлены
- **Приоритет:** INFO  
- **Область:** Документация / HTTPS  
- **Статус:** подтверждено документацией  
- **Пути:** docs/ops/*, docs/FINAL_DEPLOYMENT_CHECKLIST.md  
- **Обнаружено:** хороший каркас для demo launch при выполнении ручных шагов.

### OPS-015 — Production Django fail-closed для критичных env
- **Приоритет:** INFO  
- **Область:** Конфигурация  
- **Статус:** подтверждено кодом  
- **Путь:** ackend/config/settings/production.py  
- **Обнаружено:** ImproperlyConfigured на DEBUG/SECRET_KEY/hosts/OTP/DB/Redis/YooKassa mismatch — снижает риск «тихого» плохого старта.

### OPS-016 — Рост логов/бэкапов без контроля диска
- **Приоритет:** MEDIUM  
- **Область:** Устойчивость  
- **Статус:** потенциальный риск  
- **Пути:** logs_volume в prod compose; backup prune только для локальных gz при запуске backup-all  
- **Последствия:** disk full → PG/Redis/Docker деградация.  
- **Устранение:** logrotate + disk alert + мониторинг размера backups.  
- **Сложность:** низкая/средняя.

### OPS-017 — Секреты и .env.production как единая точка отказа DR
- **Приоритет:** MEDIUM  
- **Область:** DR / Конфигурация  
- **Статус:** потенциальный риск  
- **Обнаружено:** без offline копии env/секретов восстановление VPS блокируется даже при наличии DB dump.  
- **Устранение:** secret manager / offline sealed copy (не в Git).  
- **Сложность:** низкая.

---

## 5.17. Итоговая таблица Production Readiness

| Область | Статус | Основные ограничения |
|---|---|---|
| Развёртывание | READY WITH CONDITIONS | Ручные шаги; устаревший DEPLOYMENT.md; dirty tree |
| Конфигурация | READY WITH CONDITIONS | Fail-closed prod; риск неверного env file |
| Домен и HTTPS | NOT VERIFIED | Артефакты есть; живой TLS/DNS не проверены |
| PostgreSQL Backup | NOT READY | Нет подтверждённых cron/offsite/drill |
| Disaster Recovery | NOT READY | Процедуры на бумаге; single-VPS backup risk |
| Обновления | READY WITH CONDITIONS | Ручной процесс; нет CD/rollback policy |
| Docker и сервисы | READY WITH CONDITIONS | Health/limits ok; **нет restart policy** |
| Мониторинг | NOT READY | Health без on-call алертов |
| Платежи | NOT READY (live) / READY WITH CONDITIONS (off) | Soft-launch only |
| 1С | NOT READY (постоянная работа) | Flags off; ops алерты слабые |
| Media | READY WITH CONDITIONS | Scripts есть; must include in backup set |
| Эксплуатационная документация | READY WITH CONDITIONS | Checklists сильнее DEPLOYMENT.md |

### Общий статус проекта

# **PRODUCTION READY WITH CONDITIONS**

Интерпретация:

- **Допустимый профиль сейчас:** контролируемый public demo / soft-launch **без** онлайн-оплаты и **без** write-интеграции 1С, **после** выполнения P0 ниже (особенно backup offsite+drill и restart policy + verify TLS/firewall + deploy из чистого tag).
- **Полный коммерческий production** с реальными онлайн-платежами, ПДн-критичным объёмом и 1С — **ещё не готов** (OPS-001/002/004/005 + открытые SEC/FUNC).

Не присвоен чистый **PRODUCTION READY**: backup/restore и критичные ops процедуры **не подтверждены** исполнением.

---

## 5.18. План доработок (без реализации)

### P0 — до реального запуска (даже soft-launch с ПДн/заказами)

1. **OPS-001 + OPS-007 + OPS-010** — ежедневный encrypted backup DB+Media, offsite copy, успешный restore drill на отдельной БД.  
   - Результат: доказанный RPO path.  
   - Сложность: средняя.  
2. **OPS-002** — 
estart: unless-stopped (или эквивалент) для всех prod сервисов.  
   - Результат: подъём после reboot.  
   - Сложность: низкая.  
3. **OPS-003** — release commit/tag; деплой только из него.  
   - Результат: воспроизводимость.  
   - Сложность: средняя.  
4. **OPS-011** — проверка DNS/TLS/firewall с внешней сети.  
   - Результат: закрыты лишние порты, валидный HTTPS.  
   - Сложность: низкая.  
5. **OPS-005** — не включать ЮKassa/1С; сохранить offline checkout.  
   - Зависимости: FUNC-001, SEC-003/FUNC-002, SEC-001.  
6. **OPS-017** — offline/sealed копия .env.production и backup keys.  

### P1 — вскоре после запуска

1. **OPS-004 + OPS-009 + OPS-016** — uptime /health/+сайт, алерт Celery, disk/log.  
2. **OPS-006** — единый актуальный deploy doc.  
3. **OPS-008** — tagged images + rollback notes; backup перед migrate.  
4. **OPS-013** — выровнять DB_USER defaults backup/restore.  
5. Закрытие SEC/FUNC P0 перед любым online pay.

### P2 — плановые

1. **OPS-012** — утвердить RPO/RTO.  
2. Payment/1С operator runbooks + мониторинг pending/sync lag.  
3. Log retention policy; media growth review.

### P3 — перспективные

1. CD pipeline; blue/green или staging slot.  
2. PITR / managed Postgres.  
3. Централизованные метрики latency/5xx.

---

## 5.19. Сопоставление с предыдущими блоками

| ID | Эксплуатационный аспект |
|---|---|
| SEC-001 / FUNC-010 | После запуска staff может видеть чужие заказы без MFA admin_api — риск поддержки/комплаенса; не чинить через ops alone |
| SEC-003 / FUNC-002 | Admin cancel без release → складской хаос; restore DB не чинит бизнес-логику |
| FUNC-001 | Зависит от Celery Beat (OPS-009); при online pay критично |
| FUNC-004 / FUNC-011 | Ошибки цвета/корзины после инцидентов усугубляют ручную сверку заказов |
| FUNC-006 / FUNC-007 | Промо/бонусы — поддержка без полных API усложняет ops |
| TECH-* (B4) | Большие модули/дубли провайдеров повышают риск ошибочного hotfix на VPS (OPS-003) |

Новые дубликаты SEC/FUNC/TECH **не создавались**; добавлены только OPS-*.

---

## 5.20. Проверки, которые не выполнялись (и почему)

- Реальный deploy / compose up / rebuild images — меняет состояние.  
- Установка cron, создание backup, restore DB/Media — запрещено ТЗ.  
- DNS lookup / смена firewall / TLS issuance — риск изменения/внешние эффекты; docs уже NOT VERIFIED.  
- Реальные платежи / return / 1С write — запрещено.  
- Чтение значений секретов из .env — запрещено выводить; не копировались.  
- Подтверждение Sentry DSN получателей — нет в безопасном виде.

---

### Метаданные завершения Блока №5

- **Дата:** 2026-11-05  
- **Статус:** завершён (статический + чтение скриптов/compose/docs)  
- **Новых OPS:** 17 (CRITICAL 2 · HIGH 3 · MEDIUM 8 · LOW 2 · INFO 2)  
- **Общий вердикт:** PRODUCTION READY WITH CONDITIONS  
- **Подтверждение:** исходники/конфиги/БД/Docker/Git/VPS/DNS **не изменялись**; реальные платежи и изменяющие 1С-запросы **не выполнялись**; Блоки №1–4 сохранены; раздел №5 добавлен в конец docs/audit/RINGO_FULL_AUDIT.md

---

# ЭТАП ИСПРАВЛЕНИЙ №1. РЕЗУЛЬТАТЫ УСТРАНЕНИЯ ПРОБЛЕМ БЛОКОВ №1–2

**Дата:** 2026-11-05  
**Режим:** точечные исправления SEC-001…SEC-005; анализ SEC-006…SEC-009 без реализации  
**Git:** ветка main, HEAD до правок 8a0bd5f; commit/push **не** выполнялись; существующие незакоммиченные изменения сохранены  
**Тесты:** python manage.py test … --settings=config.settings.test — **58 passed / 0 failed** (целевой набор ниже)

## Сводная таблица

| ID | Исходная проблема | Статус | Изменённые файлы | Тесты |
|---|---|---|---|---|
| SEC-001 | Staff bypass на customer orders/payments API | FIXED | orders/views.py, payments/views.py, dmin_api/views/orders.py, dmin_api/urls.py, rontend/.../orders.service.ts, rontend/.../admin/orders/page.tsx, 	ests/test_admin_integrity.py, 	ests/test_sec001_staff_order_access.py | 	est_sec001_*, 	est_admin_integrity, OrderPaymentAccessSecurityTests |
| SEC-002 | Unapproved reviews + email в публичном API | FIXED | content/views.py, content/serializers.py, dmin_api/views/content.py, content/tests.py, dminContent.service.ts, 	ests/test_sec002_public_reviews.py | 	est_sec002_*, TestContentAPI |
| SEC-003 | Admin cancel без release резерва | FIXED | dmin_api/views/orders.py (уже в SEC-001), orders/admin.py, 	ests/test_sec003_cancel_releases_stock.py | 	est_sec003_* (assert 
eserved_quantity) |
| SEC-004 | Нет throttle на create review | FIXED | config/throttling.py, config/settings/base.py, content/views.py, 	ests/test_sec004_review_throttle.py | 	est_sec004_* → 429 |
| SEC-005 | Глобальный idempotency namespace | FIXED | orders/views.py (_order_idempotency_cache_key), 	ests/test_sec005_order_idempotency.py | 	est_sec005_* |
| SEC-006 | Guest knowledge-factor access | NEEDS DECISION | — (анализ) | — |
| SEC-007 | YooKassa webhook AllowAny | NEEDS DECISION | — (анализ) | — |
| SEC-008 | Dormant bonus admin IsStaff | NOT FIXED (dormant OK) | — (анализ; маршруты по-прежнему закомментированы) | — |
| SEC-009 | Нет password-reset API | NEEDS DECISION | — (анализ) | — |

---

## SEC-001 — FIXED

**Было:** is_staff снимал owner-filter на list/detail и разрешал cancel/pay чужих заказов без MFA/групп admin_api.

**Сделано:**
- Customer GET /orders/, GET /orders/{id}/, cancel, _can_access_order (pay/status) — только владелец (staff со своим заказом — да).
- Добавлены GET /api/v1/admin/orders/ и GET /api/v1/admin/orders/{id}/ с dmin_permissions(RINGOO_GROUP_ORDERS).
- Admin UI переведён на getAdminOrders / getAdminOrder.

**Почему безопаснее:** административный контур отделён от покупательского; MFA+RBAC не обходится JWT staff на customer API.

**Ограничения:** гостевой track/cancel/pay по order_number+phone без изменений (SEC-006).

---

## SEC-002 — FIXED

**Было:** ?is_approved=false отдавал скрытые отзывы; публичный serializer включал email.

**Сделано:** публичный queryset всегда is_approved=True; email убран из публичного ReviewSerializer; в admin content serializer email добавлен.

**Тесты:** anon не видит pending; параметр false не утекает; admin list с email для pending.

---

## SEC-003 — FIXED

**Было:** admin PATCH status=cancelled и Django Admin save только меняли статус без cancel_order_and_release_stock.

**Сделано:** admin_api PATCH при переходе в cancelled вызывает сервис; Django Admin save_model — то же. Повторная отмена идемпотентна (release только при was_active).

**Доказательство тестов:** stock.reserved_quantity уменьшается ровно на qty заказа; повтор не over-release; запрещённый переход COMPLETED→CANCELLED сохраняет резерв.

---

## SEC-004 — FIXED

**Сделано:** scopes 
eview_create_anon 10/hour, 
eview_create 20/hour; apply только на create; list использует read throttles.

---

## SEC-005 — FIXED

**Сделано:** cache key order_idempotency:{u:userId|g:sha256(session)}:{sha256(key)}. Guest без session получает session через session.create().

**Тесты:** same user dedupe; разные users/guests с одним key — разные заказы.

---

## SEC-006 — NEEDS DECISION (анализ)

- **Сейчас:** гость идентифицируется order_number + нормализованный phone (+ UUID в path для cancel/pay).
- **Риски:** утечка SMS/email/return URL → точечный доступ к одному заказу.
- **Минимальное усиление:** signed guest token (HMAC) в письме/SMS и в return URL вместо «голого» UUID+phone; FE: передавать token; BE: проверять signature+TTL. Альтернатива — одноразовый ccess_token в Order.
- **FE/BE:** оба слоя; не ломать старые ссылки — grace period dual-accept.

## SEC-007 — NEEDS DECISION (анализ)

- Webhook AllowAny + PaymentCallbackAnonThrottle (120/min); paid только после re-fetch YooKassa API.
- **Достаточно ли:** для подделки оплаты — да (re-fetch). Для DoS/abuse API YK — throttle смягчает, но не исключает.
- **Варианты без ломки архитектуры:** ужестошить throttle webhook; shared secret header если появится у провайдера; IP allowlist только после сверки актуальных диапазонов ЮKassa (не внедрять вслепую).

## SEC-008 — dormant (без включения)

- dmin_api/views/bonus.py — IsStaff без MFA/групп.
- URL в dmin_api/urls.py и публичный bonus в pi_urls.py **закомментированы**.
- **До включения:** dmin_permissions(RINGOO_GROUP_…) + MFA; отдельная группа bonus; тесты RBAC.

## SEC-009 — NEEDS DECISION (анализ)

- Публичного password-reset endpoint нет.
- **Минимальный вариант:** DRF endpoint + Django password reset token; throttle; ответ без user enumeration; email/SMS канал.
- **Не реализовывать** без продуктового решения (телефон как login id).

---

## Регрессия (запущено)

`
tests.test_sec001_staff_order_access
tests.test_sec002_public_reviews
tests.test_sec003_cancel_releases_stock
tests.test_sec004_review_throttle
tests.test_sec005_order_idempotency
tests.test_admin_integrity
tests.test_payment_security.OrderPaymentAccessSecurityTests
apps.content.tests.TestContentAPI
`

**Результат:** 58 OK, 0 failed.

Не запускались: полный suite, внешние ЮKassa/1С/Sber live, frontend vitest (контракт admin orders расширен совместимо).

---

### Метаданные этапа исправлений №1

- Исходный код изменён точечно по SEC-001…005  
- Production БД / VPS / DNS / deploy / реальные платежи / 1С write — **не** трогались  
- Git commit/push — **не** выполнялись  
- Предыдущие блоки аудита №1–5 сохранены  

---

# Этап исправлений №2 — SEC-006–SEC-009

**Дата:** 2026-11-05  
**Режим:** реализация и тесты SEC-006…SEC-009; без commit/push/deploy; без реальных платежей и писем покупателям  
**Git:** ветка `main`, HEAD `8a0bd5f814fa86e1f09404efb2a886ea1fe879da`; существующие незакоммиченные изменения сохранены  

| SEC | Кратко | Статус |
|---|---|---|
| SEC-006 | Guest access token (hash + TTL) | FIXED |
| SEC-007 | YooKassa webhook harden (throttle/size/validate/debounce) | FIXED |
| SEC-008 | Bonus admin RBAC+MFA; маршруты выключены | FIXED |
| SEC-009 | Password reset API + FE; anti-enum; blacklist refresh | FIXED (SMTP prod — внешний блокер эксплуатации) |

---

## SEC-006 — FIXED

### Первоначальная проблема
Гостевой доступ к заказу/отмене/оплате опирался на knowledge factor `order_number` + `phone` (+ UUID в path). Этого недостаточно как секрета.

### Подтверждение в исходном коде
До исправления track/cancel/pay принимали совпадение номера и телефона без криптостойкого секрета (`orders/views.py`).

### Причина
Удобство гостевого checkout без аккаунта; секретность номера+телефона переоценена.

### Архитектурное решение
- При создании гостевого заказа выдаётся `guest_access_token` (`secrets.token_urlsafe(32)`).
- В БД хранится только SHA-256 хеш + `guest_access_token_expires_at` (TTL по умолчанию 90 дней, `ORDER_GUEST_ACCESS_TOKEN_TTL_DAYS`).
- Сравнение через `secrets.compare_digest`.
- Полные ПДн / cancel / pay — только с валидным токеном.
- Без токена track отдаёт урезанный статус (без контактов/адреса/состава).
- Legacy: заказы **без** хеша сохраняют временный phone+number доступ (переходный период).
  - **[INT-028 / актуально 2026-11-06]** legacy full-access по phone+number **закрыт** (SEC-006 acceptance). Без валидного `guest_token` — только урезанный статус. Восстановление полного доступа — email OTP (`/orders/guest-access/recover/`). Для заказов без email recovery недоступен. SMTP обязателен для production recover.
- FE: токен сохраняется локально после checkout и передаётся в track/cancel/pay/return.

### Изменённые / новые файлы
- `backend/apps/orders/guest_access.py` (новый)
- `backend/apps/orders/migrations/0009_order_guest_access_token.py` (новый)
- `backend/apps/orders/models.py`, `views.py`, `serializers.py`
- `frontend`: checkout, orders/[id], payments/orders services, types
- `backend/tests/test_sec006_guest_access_token.py`

### Миграции
`0009_order_guest_access_token` — обратимая; **не** применялась на production в рамках этапа.

### Меры безопасности
Хеш вместо plaintext; TTL; constant-time compare; токен не логируется; привязка к одному заказу; admin API не затронут.

### Тесты
11 тестов в `tests/test_sec006_guest_access_token.py` (token OK/deny, cross-order, phone без token, expire, owner, cancel/pay, create).

### Команды
```
DJANGO_SETTINGS_MODULE=config.settings.test python -m pytest tests/test_sec006_guest_access_token.py -q --no-cov
```
**Результат:** 11 passed.

### Остаточные риски
- Legacy заказы без хеша всё ещё доступны по phone+number до истечения/миграции данных.
  - **[INT-028]** устарело: после acceptance Stage2 phone+number **не** даёт полный доступ; см. `guest_access.py` + `test_sec006_*`.
- Утечка plaintext токена из локального storage / пересланной ссылки даёт доступ к одному заказу до TTL.
- Миграцию нужно применить на целевых средах перед деплоем.
- Email OTP recovery зависит от SMTP (без SMTP в production — recover не работает).

### Итоговый статус
**FIXED** (legacy full access закрыт; INT-028 уточняет документацию)

---

## SEC-007 — FIXED

### Первоначальная проблема
Webhook ЮKassa публичный (AllowAny); риск abuse/DoS и лишних вызовов API ЮKassa. Подделка PAID без re-fetch уже была невозможна, но защита от злоупотреблений была слабой.

### Подтверждение
`YooKassaWebhookView` AllowAny; истина оплаты — `sync_payment_from_yookassa` / re-fetch.

### Причина
Официальный протокол ЮKassa без HMAC-подписи уведомлений; доверие строится на серверной сверке.

### Архитектурное решение (без ослабления re-fetch)
- Отдельный `YooKassaWebhookThrottle` (scope `yookassa_webhook`).
- Лимит размера тела (`YOOKASSA_WEBHOOK_MAX_BODY_BYTES`, default 64 KiB) → 413.
- Валидация JSON/структуры; неизвестные/игнорируемые event не запускают тяжёлую сверку без нужды.
- Debounce повторных sync одного payment (`yk_webhook_sync:{pk}`) — снижает storm к API ЮKassa.
- PAID по-прежнему только после успешной проверки id/суммы/валюты/metadata/связки с заказом.
- IP allowlist **не** внедрён: ненадёжен за reverse proxy без подтверждённых диапазонов; не единственный фактор доверия.

### Изменённые файлы
- `backend/apps/payments/views.py`, `yookassa_service.py`
- `backend/config/throttling.py`, `settings/base.py`, `settings/test.py`
- `backend/tests/test_sec007_yookassa_webhook.py`

### Тесты
9 тестов: forged succeeded без API; wrong amount/currency/metadata; unknown id; invalid JSON; oversized; valid once; ignored event.

### Команды
```
DJANGO_SETTINGS_MODULE=config.settings.test python -m pytest tests/test_sec007_yookassa_webhook.py tests/test_yookassa_payments.py -q --no-cov
```
**Результат:** SEC-007 9 passed; yookassa_payments 16 passed (в регрессии этапа).

### Остаточные риски
- Публичный endpoint остаётся; IP allowlist отложен до подтверждения диапазонов + корректного trusted proxy.
- При недоступности API ЮKassa webhook не ставит PAID (ожидаемо); сверка Celery остаётся запасным каналом.

### Итоговый статус
**FIXED**

---

## SEC-008 — FIXED (модуль выключен)

### Первоначальная проблема
Dormant bonus admin views с `IsStaff` — при будущем подключении URL любой staff получил бы финансовые операции с бонусами.

### Подтверждение
`admin_api/views/bonus.py` ранее ослабленные permissions; URL закомментированы.

### Причина
Черновик модуля до полной RBAC-модели.

### Архитектурное решение
- Группа `RINGOO_GROUP_BONUS = "ringoo_bonus"`.
- Views: `admin_permissions(RINGOO_GROUP_BONUS)` (+ MFA claim как у прочих admin_api).
- Корректировка баланса через сервис `admin_adjust`; actor в аудите/описании.
- URL bonus в `admin_api/urls.py` и публичный bonus **остаются закомментированными** — модуль не включён.
- Frontend бонусов не активировался.

### Изменённые файлы
- `backend/apps/admin_api/permissions.py`, `views/bonus.py`, `urls.py`
- `backend/tests/test_sec008_bonus_permissions.py`

### Тесты
10 тестов: anon/plain staff/wrong group deny; bonus group+MFA allow; URLs not mounted; concurrency adjust; actor recorded.

### Команды
```
DJANGO_SETTINGS_MODULE=config.settings.test python -m pytest tests/test_sec008_bonus_permissions.py -q --no-cov
```
**Результат:** 10 passed.

### Остаточные риски
- До включения в production нужно создать группу `ringoo_bonus`, назначить операторов, проверить MFA enrollment.
- Не включать маршруты без отдельного продуктового решения.

### Итоговый статус
**FIXED** (код готов; runtime-модуль выключен намеренно)

---

## SEC-009 — FIXED (SMTP — внешняя настройка)

### Первоначальная проблема
Публичного процесса восстановления пароля не было (вход по телефону без reset-потока).

### Подтверждение
Отсутствовали endpoints password-reset в `users/urls.py`.

### Причина
Фокус на phone/password login; email recovery не был реализован.

### Архитектурное решение
- `POST /api/v1/auth/password-reset/` — одинаковый публичный ответ (anti-enumeration).
- Токен: Django `PasswordResetTokenGenerator` + uidb64; одноразовость через смену password hash.
- `POST /api/v1/auth/password-reset/confirm/` — validators Django; `set_password`.
- После смены: blacklist OutstandingToken пользователя (refresh).
- Throttle: `password_reset` 5/hour, `password_reset_confirm` 10/hour; доп. лимит писем на email в cache (3/час).
- FE: `/forgot-password`, `/reset-password?uid=&token=`, ссылка с login.
- Тесты: locmem email backend; реальные письма не отправлялись.

### Изменённые / новые файлы
- `backend/apps/users/password_reset.py` (новый)
- `backend/apps/users/urls.py`
- `backend/config/throttling.py`, `settings/base.py`, `settings/test.py`
- `frontend/src/lib/api/services/auth.service.ts`
- `frontend/src/app/login/page.tsx`
- `frontend/src/app/forgot-password/page.tsx` (+ test)
- `frontend/src/app/reset-password/page.tsx` (+ test)
- `backend/tests/test_sec009_password_reset.py`

### Миграции
Не требуются (стандартный Django token generator).

### Тесты
Backend: 5 passed. Frontend Vitest: 2 passed (`forgot-password`, `reset-password`).

### Команды
```
DJANGO_SETTINGS_MODULE=config.settings.test python -m pytest tests/test_sec009_password_reset.py -q --no-cov
npx vitest run src/app/forgot-password/page.test.tsx src/app/reset-password/page.test.tsx
```

### Внешние настройки (эксплуатация)
- Рабочий SMTP / email backend в production (`EMAIL_*`, `DEFAULT_FROM_EMAIL`).
- `FRONTEND_URL` должен указывать на публичный origin магазина (ссылка в письме).
- Пользователи без email не смогут восстановить пароль этим каналом (вход по телефону) — продуктовый остаток.

### Остаточные риски
- Access JWT до истечения TTL остаётся валидным (стандарт SimpleJWT); отозваны refresh через blacklist.
- Rate-limit по email не мешает чужому IP полностью «закрыть» аккаунт навсегда (окно 1 час / 3 письма).

### Итоговый статус
**FIXED** (код+тесты); доставка писем в prod — **NEEDS EXTERNAL CONFIGURATION** (SMTP)

---

## Регрессия этапа №2 (фактически запущено)

```
tests/test_sec001_staff_order_access.py
tests/test_sec002_public_reviews.py
tests/test_sec003_cancel_releases_stock.py
tests/test_sec004_review_throttle.py
tests/test_sec005_order_idempotency.py
tests/test_sec006_guest_access_token.py
tests/test_sec007_yookassa_webhook.py
tests/test_sec008_bonus_permissions.py
tests/test_sec009_password_reset.py
tests/test_yookassa_payments.py
tests/test_order_repay.py
```

**Результат:** 101 passed, 0 failed.

Frontend Vitest (целевой): 2 passed (`forgot-password`, `reset-password`).

**Не запускались:** полный backend suite целиком; полный frontend Vitest suite; live ЮKassa/1С/SMTP; apply migration на prod.

---

### Метаданные этапа исправлений №2

- Исходный код изменён по SEC-006…009  
- Production БД / VPS / DNS / deploy / реальные платежи / реальные письма / 1С write — **не** трогались  
- Git commit/push — **не** выполнялись  
- Предыдущие блоки аудита №1–5 и этап №1 сохранены; раздел этапа №2 добавлен в конец  

---

# Финальная приёмка этапа исправлений №2

**Дата:** 2026-11-05  
**Git:** `main` @ `8a0bd5f814fa86e1f09404efb2a886ea1fe879da` (без commit/push)  

| SEC | Итог приёмки |
|---|---|
| SEC-006 | **FIXED** — legacy phone+number закрыт; recovery через email OTP |
| SEC-007 | **FIXED** — доп. тесты API down / retry / идемпотентность |
| SEC-008 | **FIXED** — модуль выключен; RBAC+MFA на views |
| SEC-009 | **FIXED** (код/тесты); SMTP/FRONTEND_URL — **NEEDS EXTERNAL CONFIGURATION** |

---

## SEC-006 — результат проверки

### Обнаружено дополнительно
Legacy fallback в `guest_may_access_order` всё ещё давал полный доступ по `order_number`+`phone` для заказов без хеша. Страница `/order-status` и часть payment-тестов опирались на этот путь. Оценка менеджера (`/orders/rate/`) тоже принимала phone+number.

### Исправления
1. Удалён legacy phone+number из `guest_may_access_order` — доступ только по валидному `guest_token`.
2. Track/status без токена: только урезанный статус (`guest_token_required`), без ПДн — и для новых, и для старых заказов.
3. Добавлены endpoints:
   - `POST /api/v1/orders/guest-access/recover/`
   - `POST /api/v1/orders/guest-access/recover/confirm/`
4. Recovery: одноразовый криптостойкий токен в cache (hash), письмо на email заказа; anti-enumeration; throttle; без SMS (инфраструктуры нет).
5. Заказы без email: публичный ответ тот же, письмо не уходит — нужен контакт поддержки / повторное оформление с email.
6. FE: `/order-status` — восстановление доступа + обработка ссылки из письма; sessionStorage для guest_token.
7. Cancel/pay/rate/payment status требуют guest_token для гостя.
8. Регрессионные тесты payment/sber/sec001 обновлены под новый gate.

### Тесты
`tests/test_sec006_guest_access_token.py` — 16 passed, в т.ч. **тест №2** `test_legacy_order_without_hash_denied_pii_by_phone`.

### Legacy-доступ устранён?
**Да.** Знание номера и телефона больше не даёт ПДн, отмену или оплату. Восстановление — только после подтверждения email OTP.

### Ограничения
- Без email на заказе авто-восстановление невозможно (нет SMS-канала).
- Миграция `0009` должна быть применена на целевых средах (не production в рамках задачи).
- Урезанный статус по phone+number всё ещё подтверждает совпадение телефона (без ПДн).

### Статус: **FIXED**

---

## SEC-007 — результат проверки

### Проверено
Re-fetch API, сумма/валюта/metadata, debounce, size limit, throttle, идемпотентность повторных webhook, API unavailable → не PAID, восстановление после ошибки → PAID, Celery `reconcile_open_payments_task` сохранён.

### Доп. исправления
- `handle_yookassa_webhook` ловит неожиданные ошибки API (не только `PaymentError`) без установки PAID.
- Добавлены тесты: API down, recover after failure, repeated webhooks.

### IP allowlist
Не внедрялся (неподтверждённые диапазоны / reverse proxy).

### Статус: **FIXED**

---

## SEC-008 — результат проверки

### Проверено
Views требуют `admin_permissions(RINGOO_GROUP_BONUS)` + MFA; URL admin/public **закомментированы**; checkout `bonus_used: '0'`; frontend бонусов не активирован; concurrent adjust покрыт тестами.

### Доп. проблем не найдено
Код бонусного модуля не включался.

### Статус: **FIXED** (модуль выключен)

---

## SEC-009 — результат проверки

### Проверено
Anti-enumeration, Django token generator, одноразовость, validators, blacklist refresh, throttle, FE pages, locmem email в тестах. Секреты не хардкодятся; `FRONTEND_URL` / `EMAIL_*` из settings/env.

### Внешние настройки
- Production SMTP (`EMAIL_HOST`, credentials, `DEFAULT_FROM_EMAIL`)
- Корректный публичный `FRONTEND_URL`

### Статус: **FIXED** (эксплуатация писем — **NEEDS EXTERNAL CONFIGURATION**)

---

## Регрессия финальной приёмки

### Целевые + платежи
SEC-001…009 + yookassa + repay + payment_security + sber — в составе полного suite.

### Полный backend suite
```
DJANGO_SETTINGS_MODULE=config.settings.test python -m pytest -q --no-cov
```
**255 passed, 6 skipped, 0 failed**  
Skipped: postgres concurrency (нет PG) + 1 onec skip.

### Полный frontend Vitest
```
npx vitest run
```
**34 files / 90 tests passed**

### Миграции
- Файл: `orders/migrations/0009_order_guest_access_token.py`
- Depends on: `0008_order_checkout_cart_id`
- Операции: AddField hash + expires_at (обратимо через reverse AddField)
- `makemigrations --check --dry-run`: No changes detected
- Conflicts: не обнаружены (disk graph)
- Production migrate: **не** выполнялся
- Test settings отключают `MIGRATION_MODULES` — apply на test DB через sync models; для staging/prod нужен обычный migrate

---

### Метаданные финальной приёмки №2

- Legacy guest access закрыт и подтверждён тестом №2  
- Production/DNS/deploy/commit/push/реальные письма/платежи — **не** выполнялись  
- Незакоммиченные пользовательские изменения сохранены  

---

# Блок исправлений №3 — FUNC-001–FUNC-011

**Дата:** 2026-11-05  
**Git:** `main` @ `8a0bd5f814fa86e1f09404efb2a886ea1fe879da` (commit/push не выполнялись)  
**Контекст:** после SEC-001…009; guest_token / YK re-fetch / bonus RBAC / password reset сохранены.

| FUNC | Статус |
|---|---|
| FUNC-001 | FIXED |
| FUNC-002 | FIXED / ALREADY FIXED (пути унифицированы + paid gate) |
| FUNC-003 | FIXED |
| FUNC-004 | FIXED |
| FUNC-005 | FIXED |
| FUNC-006 | NEEDS BUSINESS DECISION |
| FUNC-007 | FIXED |
| FUNC-008 | ALREADY FIXED (регрессия OK) |
| FUNC-009 | FIXED |
| FUNC-010 | ALREADY FIXED (регрессия OK) |
| FUNC-011 | FIXED |

---

## FUNC-001 — FIXED

**Проблема:** `expire_unpaid_online_orders` синкал только Sber перед отменой.  
**Решение:** sync Sber + YooKassa; при ошибке API — `skipped_uncertain`, без слепой отмены; PAID → rescued.  
**Файлы:** `payments/services.py`; `tests/test_func001_expire_yookassa_sync.py`.  
**Тесты:** 7 passed (+ sber expire).  
**Риски:** при длительной недоступности API заказы ждут следующего beat.

## FUNC-002 — FIXED

**Проблема:** разные пути отмены.  
**Состояние:** customer / admin_api / Django Admin / Celery expire → `cancel_order_and_release_stock`. Bulk cancel action отсутствует (только confirmed bulk).  
**Усиление:** сервис с paid-guard; admin PATCH ловит `OrderCancelError`.  
**Тесты:** `test_func002_func009_*` + `test_sec003_*`.

## FUNC-009 — FIXED

**Проблема:** отмена confirmed после PAID.  
**Решение:** `order_has_successful_payment` / `customer_may_cancel_order`; customer+admin запрет без refund flow (`allow_paid=False`); поле `can_cancel` в API.  
**Refund:** не реализован автоматически — **NEEDS BUSINESS DECISION** для процесса возврата.  
**Тесты:** paid cancel denied (user/guest/admin).

## FUNC-011 — FIXED

**Проблема:** цвет корзины не попадал в заказ.  
**Решение:** OrderItem + color FK + snapshots (label/slug/hex); create принимает `color_id`; цена из `effective_price`; обязательный цвет если у товара есть активные цвета; FE checkout передаёт `color_id`.  
**Миграция:** `orders/0010_orderitem_color_snapshot`.  
**1С:** код цвета в 1С не выдуман — snapshot в заказе; ограничение интеграции задокументировано.  
**Тесты:** `test_func011_func004_color_and_cart.py`.

## FUNC-004 — FIXED

**Проблема:** clear по product_id FIFO.  
**Решение:** сопоставление product+color (+ предпочтение store).  
**Файл:** `cart/checkout_clear.py`.  
**Тесты:** два цвета — снимается нужная линия.

## FUNC-003 — FIXED

**Проблема:** price_at_add vs Product.price.  
**Решение:** `expected_unit_price` + `accept_price_changes`; при расхождении 400 `price_changed` с новым итогом; FE чекбокс подтверждения.  
**Тесты:** `test_func003_price_consistency.py`.

## FUNC-005 — FIXED

**Проблема:** нет кнопки отмены в ЛК detail.  
**Решение:** кнопка на `orders/[id]` при `can_cancel`; confirm dialog; блокировка submit.  
**Файлы:** `orders/[id]/page.tsx`.

## FUNC-007 — FIXED

**Проблема:** signals начисляли бонусы при выкл. API.  
**Решение:** `BONUS_ENABLED` (env, default False); signal и spend gated; URLs не подключены.  
**Тесты:** `test_func007_bonus_flag.py`.

## FUNC-006 — NEEDS BUSINESS DECISION

**Проблема:** validate промокода есть, apply к заказу нет.  
**Решение в коде:** не внедряли apply — не хватает политики (совместимость акций, лимиты на user, возврат скидки, поля Order). Checkout остаётся с явной заглушкой.  
**Вопросы владельцу:** см. финальный отчёт, часть Д.

## FUNC-008 / FUNC-010 — ALREADY FIXED

Регрессия: `test_sec002_*`, `test_sec001_*` — passed.

---

## Регрессия блока №3

```
DJANGO_SETTINGS_MODULE=config.settings.test python -m pytest -q --no-cov
→ 279 passed, 6 skipped

npx vitest run → 90 passed / 34 files
npx next build → success
```

Миграции disk: orders 0001…0010, conflicts {}. Production migrate не запускался.

---

### Метаданные блока исправлений №3

- SEC-001…009 не откатывались  
- commit/push/deploy/DNS/реальные платежи/письма/1С write — **нет**  
- Исходный Блок №3 аудита не переписывался

---

# БЛОК №4. ИНТЕГРАЦИОННЫЙ И ЭКСПЛУАТАЦИОННЫЙ АУДИТ

**Дата проведения:** 2026-11-06  
**Режим:** READ-ONLY (единственное изменение — append этого раздела)  
**Контекст:** после исправлений SEC-001…009 и FUNC-001…011; предыдущие разделы файла (в т.ч. ранее названные «Блок №4 TECH» и «Блок №5 ops») **не переписывались**. Нумерация заголовка соответствует брифу заказчика на интеграционный аудит.  
**Git (RO):** ветка `main`, HEAD `8a0bd5f814fa86e1f09404efb2a886ea1fe879da`, dirty working tree ~274 porcelain entries (исправления SEC/FUNC локально, не закоммичены).  
**Ограничения:** без реальных платежей, без write в 1С/ЮKassa/Сбер, без migrate на staging/prod, без DNS/VPS изменений, без commit/push.

---

### 1. Общий вывод

- **Общая оценка:** после блоков безопасности и функциональных исправлений **ядро checkout → оплата → резерв → отмена** в коде выглядит согласованным и регрессионно подтверждённым unit/API-тестами с моками. Интеграционная целостность «сайт ↔ реальные внешние системы ↔ VPS» **не доказана**.
- **Готовность к staging:** **условно да** для `test.ringoo15.store` при: tagged/чистом деплое незакоммиченных SEC/FUNC, migrate 0009/0010 на тестовой БД, Basic Auth/IP allowlist, `YOOKASSA_ENABLED=1` + `YOOKASSA_TEST_MODE=1`, Celery worker+beat, SMTP sandbox, 1С-флаги по решению. Без этого staging будет неполным.
- **Готовность к production (`ringoo15.store`):** **нет** для полного коммерческого контура (live-оплата + 1С + DR). Допустима только осторожная demo/soft-launch модель с выключенной онлайн-оплатой и 1С — и то после P0 ops (backup offsite+drill, TLS/firewall verify, мониторинг).
- **Критические ограничения:**
  1. Реальные ЮKassa / Сбер / 1С / VPS / restore drill — **NOT TESTED**.
  2. Concurrency stock — тесты на PostgreSQL **skipped** (6 skipped).
  3. Нет автоматического refund-flow; отмена оплаченного запрещена (корректно), но операционный возврат денег не закрыт.
  4. Django Admin bulk/свободные смены статуса обходят FSM admin_api.
  5. Webhook `refund.succeeded` не переводит локальный Payment в `refunded` (no-op при уже PAID).
  6. Локальные исправления не на remote HEAD — риск деплоя «старого» кода.

---

### 2. Матрица результатов

| ID | Область | Проблема | Серьёзность | Доказательство | Файлы | Тесты | Рекомендация | Статус |
|---|---|---|---|---|---|---|---|---|
| INT-001 | Orders/Admin | Bulk «Подтверждён» делает `queryset.update(status=confirmed)` без FSM и side-effects (можно «оживить» cancelled, без 1С/резерва) | High | `action_set_status_confirmed` → прямой update | `orders/admin.py` | нет негативного теста на revive cancelled | Запретить confirm из cancelled; идти через сервис/admin_api transitions | CONFIRMED |
| INT-002 | Orders/Admin | Не-cancel смена статуса в Django Admin `save_model` не использует граф переходов admin_api | Medium | Admin API имеет ALLOWED map; Admin save — только спец-кейс cancel | `orders/admin.py`, `admin_api/views/orders.py` | FSM покрыт admin_api частично | Единый transition service для Admin и API | CONFIRMED |
| INT-003 | Payments/Refund | Автовозврат / отмена оплаченного заказа с refund отсутствует; `allow_paid` не для UI | High (ops) | `OrderCancelError` paid gate; клиент `create_refund` есть, бизнес-flow нет | `orders/services/__init__.py`, `integrations/yookassa/client.py` | paid cancel denied | Политика возврата + API + UI поддержки | NEEDS BUSINESS DECISION |
| INT-004 | Payments/Webhook | `refund.succeeded` входит в allowlist, но `sync_payment_from_yookassa` при `STATUS_PAID` сразу return — локальный статус refunded не выставляется | High | early-return PAID; нет ветки refund object | `payments/yookassa_service.py` | webhook tests без refund.succeeded→refunded | Обработать refund event отдельно / GET refunds | CONFIRMED |
| INT-005 | Payments/Binding | Пустые `metadata.order_id`/`payment_id` не отклоняют succeeded (проверка только при непустых значениях) | Medium | `_reject_untrusted_yk_paid`: `if meta_order and …` | `payments/yookassa_service.py` | amount/currency mismatch покрыты | Требовать обязательные metadata поля | CONFIRMED |
| INT-006 | Payments/Late | Default `LATE_ONLINE_PAYMENT_POLICY=manual`; для YK `reverse` принудительно → manual (деньги могут «зависнуть» до ручной сверки) | High (ops) | policy env + YK reverse→manual | `payments/services.py`, `settings/base.py` | late policy Sber tests | Runbook + алерты NEEDS_REVIEW; решение revive vs refund | CONFIRMED |
| INT-007 | Celery | Нет distributed lock на expire/reconcile; при двух beat/worker возможны параллельные проходы (смягчено `select_for_update`) | Medium | tasks без lock; beat schedule 3–5 мин | `payments/tasks.py`, `settings/base.py` | идемпотентность expire в unit | Redis lock / single beat instance | CONFIRMED |
| INT-008 | Stock | Concurrency «два покупателя на последний товар» на PostgreSQL **не прогнан** в этой среде | High (uncertainty) | `test_concurrency_postgres` skipped ×6 | `tests/test_concurrency_postgres.py`, `stores/models.py` | skipped | Прогнать на PG staging | NOT TESTED |
| INT-009 | Stock | Сетевой release без журнала резерваций — приближённое снятие (`release_across_stores`) | Medium | docstring «без журнала» | `stores/models.py` | unit reserve atomic | Журнал reservation per OrderItem | CONFIRMED |
| INT-010 | 1С | Цвет сайта → 1С: в payload уходит `onec_code` + `seriesId`, не ProductColor snapshot; расхождение витрины и 1С возможно | Medium | builder payload series/code | `integrations/onec/orders.py`, mig 0010 | mocks `test_onec_orders` | Бизнес-маппинг цвет↔series/код | NEEDS BUSINESS DECISION |
| INT-011 | 1С | Реальная недоступность/дубликаты/потеря ответа на проде **не проверялись**; retry/status machine есть в коде | High (ext) | sync statuses + Celery retry | `integrations/onec/orders.py`, `orders/tasks.py` | mocks only | Staging drill с тестовой 1С | NOT TESTED |
| INT-012 | Migrations | 0009 guest token + 0010 color snapshot nullable/safe defaults; конфликтов файлов нет; **apply на staging/prod запрещён и не делался** | Medium | mig files; leaf 0010 | `orders/migrations/0009_*`, `0010_*` | модели в test DB | Pre-backup + migrate на staging | NOT TESTED (live) |
| INT-013 | Backup/DR | Скрипты dump/restore/age есть; cron/offsite/restore drill — не подтверждены | High (ops) | docs/ops/BACKUP_AND_RESTORE.md «NOT VERIFIED» | `scripts/backup-*.sh`, docs | n/a | Offsite + drill до live pay | NOT TESTED |
| INT-014 | VPS/Deploy | Prod compose закрывает DB/Redis ports, soft-launch flags off; живой AdminVPS/TLS/DNS — нет | High (ops) | `docker-compose.prod.yml` | compose, ops docs | n/a | Staging VPS checklist | NOT TESTED |
| INT-015 | FE/UX | `needs_review` на return page показывается в ветке «failed» | Low | `failed = … \|\| needs_review` | `orders/[id]/payment/return/page.tsx` | return page logic | Отдельный UI «на проверке» | CONFIRMED |
| INT-016 | Promo | Apply промокода к заказу отсутствует | Medium (biz) | validate-only (Block3) | promotions / checkout | — | Политика скидок | NEEDS BUSINESS DECISION / FIXED earlier as deferred |
| INT-017 | Bonus | `BONUS_ENABLED` default False; скрытое начисление выкл. | Info | settings + signals gate | `bonus/signals.py`, `settings/base.py` | `test_func007_*` | Не включать без политики | FIXED |
| INT-018 | Cart/Pay | Очистка корзины product+color+store, идемпотентна через `checkout_cart_id=None` | — | checkout_clear | `cart/checkout_clear.py` | func011/004, online_cart_retention | Сохранить | FIXED |
| INT-019 | Pay/Expire | Expire синкает YK+Sber; API fail → skip cancel; PAID → rescue | — | expire_unpaid_online_orders | `payments/services.py` | `test_func001_*` | Keep beat alive | FIXED |
| INT-020 | Cancel | Единый `cancel_order_and_release_stock`; paid forbid | — | services + admin/api paths | `orders/services/__init__.py` | func002/009, sec003 | Refund product later | FIXED |
| INT-021 | Guest | Token-only private guest access + email recover | — | guest_access + views | `orders/guest_access.py` | sec006 | — | FIXED |
| INT-022 | Webhook YK | Успех только после GET API; amount/currency/id checks; debounce | — | handle_yookassa_webhook | `yookassa_service.py` | sec007, yookassa_payments | Дополнить refund path | FIXED (paid path) |
| INT-023 | SEC staff/reviews/idempotency/throttle/MFA/reset | Ранее закрытые SEC-001…005,008,009 | — | код+тесты | соответствующие apps | sec00x suite | Не регрессировать | FIXED |
| INT-024 | FE-BE contract | `can_cancel`, `color_id`, `expected_unit_price`, guest token, return polling — согласованы | Low residual | FE services/types + BE serializers | frontend checkout/orders, BE serializers | vitest 90 | Следить за OpenAPI | CONFIRMED (aligned) |
| INT-025 | Release process | Dirty tree 274; origin HEAD без SEC/FUNC fixes | High (ops) | git status | working tree | — | Commit/tag до staging | CONFIRMED |

---

### 3. Карта интеграций

```
[Browser / Next.js]
    |  HTTPS (planned: Caddy → ringoo15.store / test.)
    v
[Next.js] --proxy/API--> [Django/DRF Gunicorn]
                              |           |
                    PostgreSQL |           | Redis (cache + Celery broker)
                              |           |
                              |           +--> Celery Worker + Beat
                              |                    |
                              |                    +--> expire / reconcile payments
                              |                    +--> 1C order sync/cancel
                              |                    +--> email notifications
                              |
                              +--> YooKassa API (create/get; webhook inbound)
                              +--> Sber Ecom (feature-flagged, legacy path)
                              +--> 1C HTTP services (client from site → 1C)
                              +--> SMTP (order mail)
                              +--> Media volume (product images)
```

**Наблюдения:** сайт — HTTP-клиент 1С (не хост 1С). PG/Redis в prod overlay без public ports. Платежный success path: webhook/return/reconcile → re-fetch провайдера → PAID → cart clear + enqueue 1С paid.

---

### 4. Карта критических бизнес-процессов

**Покупка (авторизованный / гость)**  
Cart → checkout serializer (price check, color, reserve via `plan_and_reserve_at_store`) → Order(+items snapshots) → optional `guest_access_token` → response. Идемпотентность create — SEC-005.

**Онлайн-оплата (YooKassa, primary)**  
Initiate (сумма из Order) → create у YK (Idempotence-Key=payment.id) → redirect URL → user return page **только опрашивает сайт** → webhook/reconcile → GET YK → validate amount/currency/metadata/id → PAID → order NEW→CONFIRMED → on_commit cart clear + 1С sync paid. Повтор webhook/Celery: select_for_update + early PAID return.

**Сбер**  
Код сохранён, prod default off; expire/reconcile умеют оба провайдера. Live dual-enable не рекомендуется.

**Отмена неоплаченного**  
Customer/guest/admin_api/Django Admin cancel / expire → `cancel_order_and_release_stock` → release reserve → enqueue 1С cancel. Идемпотентна.

**Отмена оплаченного**  
Запрещена (`paid_order_cancel_forbidden`) без refund product. **Разрыв процесса.**

**Поздняя оплата после cancel**  
NEEDS_REVIEW / revive / reverse(Sber); YK reverse→manual. Default manual.

**Резервирование**  
`Stock.reserve_*_atomic` с `select_for_update` + `F()` условия; series-aware для 1С. PG concurrency NOT TESTED здесь.

**Синхронизация 1С**  
Статусы onec_sync_*; retry Celery; блокировки pending_review. Реальный контур NOT TESTED.

**Восстановление после сбоя**  
Документированные backup scripts; offsite/drill NOT VERIFIED. Payment reconcile beat закрывает «webhook потерян». Cart clear идемпотентен. 1С: повтор sync по статусам, риск дублей на стороне 1С при «приняли, ответ потеряли» — зависит от 1С idempotency (NOT TESTED).

---

### 5. Технический долг

- Два «контура» смены статуса: admin_api FSM vs Django Admin bulk/free edit.
- Sber + YooKassa параллельные сервисы усложняют expire/late-policy.
- Нет task lock / observability очереди Celery.
- `docs/DEPLOYMENT.md` vs актуальный prod checklist — риск оператора.
- Uncommitted SEC/FUNC масса в working tree.
- FE: `needs_review` как failed; нет dedicated refund UI.
- Stock network release без ledger.
- Промокоды validate-only; bonus выключен.
- Concurrency suite требует PostgreSQL CI job.

---

### 6. Отсутствующие проверки

| Что | Почему не проверено |
|---|---|
| PostgreSQL concurrency stock/order | SQLite/test env; 6 skipped |
| Реальная ЮKassa (test/live) | запрет реальных платежей |
| Реальный Сбер | флаг off + запрет |
| Реальная 1С import/orders/cancel | запрет write; только mocks |
| VPS AdminVPS / DNS / TLS / firewall | запрет сетевых изменений |
| Production migrate 0009/0010 | запрет migrate prod/staging |
| Restore drill на отдельной БД | не выполнялся в этом аудите |
| Offsite backup cron | не верифицирован в окружении |
| Dual Celery Beat race | нет стенда с двумя beat |
| End-to-end browser pay | потребовал бы реальный/sandbox PSP | 

---

### 7. Рекомендации

**P0 — блокирует безопасную эксплуатацию (live pay / полный магазин)**  
1. Не включать live `YOOKASSA` / 1С sync до staging drill.  
2. Закрыть процесс возврата (бизнес + код + runbook NEEDS_REVIEW).  
3. Обработать `refund.succeeded` корректно (INT-004).  
4. Offsite backup + успешный restore drill.  
5. Закоммитить/затегить SEC+FUNC; деплоить только артефакт, не грязное дерево.  
6. Прогнать `test_concurrency_postgres` на PG.

**P1 — важно до production**  
1. Убрать/ужесточить Django Admin bulk confirm и свободные переходы (INT-001/002).  
2. Обязательные metadata при YK succeeded (INT-005).  
3. Алерты: NEEDS_REVIEW payments, Celery beat down, 1С ERROR.  
4. Staging `test.ringoo15.store` за Basic Auth/IP allowlist; migrate 0009/0010; YK TEST_MODE e2e.  
5. Single Beat + optional Redis lock на expire.  
6. Согласовать цвет витрины ↔ series/код 1С.

**P2 — желательно**  
1. UI для `needs_review`.  
2. Журнал резерваций Stock.  
3. Выровнять DEPLOYMENT.md с checklist.  
4. Промокод apply — после бизнес-решения.  
5. Мониторинг диска media/logs.

**P3 — улучшения**  
1. OpenAPI sync FE types.  
2. Упрощение/удаление мёртвого Sber path после выбора YK.  
3. Formal RPO/RTO в ops runbook.

---

### 8. Итоговый вердикт

| Область | Оценка |
|---|---|
| Корректность бизнес-логики (код+тесты) | **Хорошо с оговорками** (refund/promo/1С-цвет открыты) |
| Безопасность API (после SEC) | **Хорошо** в unit/API; live auth/TLS NOT TESTED |
| Целостность данных | **Средне+**: транзакции/идемпотентность есть; Admin bypass и stock ledger gaps |
| Платёжный контур | **Готов к sandbox staging**; **не готов к live** без refund/INT-004/ops |
| Складской учёт | **Код защищён атомарностью**; **PG concurrency NOT TESTED** |
| Интеграция 1С | **Каркас готов**; **реальный контур NOT TESTED** |
| Готовность к staging | **Условно да** (test domain + flags + commit + migrate + YK test) |
| Готовность к production | **Нет** для полного коммерческого запуска |

**Вердикт одной строкой:** система после блоков 1–3 **интеграционно согласована в коде и автотестах**, но **не подтверждена как эксплуатационно готовая** к production без внешних drills и закрытия refund/ops P0.

---

### Метаданные прогона (блок №4)

```
Backend: DJANGO_SETTINGS_MODULE=config.settings.test python -m pytest -q --no-cov
→ 279 passed, 6 skipped (test_concurrency_postgres)

Targeted subset (payments/orders/sec/func): 173 passed

Frontend: npx vitest run → 90 passed / 34 files

Реальные платежи / 1С write / migrate staging|prod / DNS / VPS — не выполнялись.
Изменён только docs/audit/RINGO_FULL_AUDIT.md (append).
```

### Addendum 4.1 — уточнения по результатам повторной сверки кода

Источник: независимый read-only code pass после основного текста Блока №4 ([Post-fix audit explore](63d57181-da0d-4389-894f-b35f09c91dd2)). Код не изменялся.

| ID | Область | Проблема | Серьёзность | Доказательство | Файлы | Тесты | Рекомендация | Статус |
|---|---|---|---|---|---|---|---|---|
| INT-026 | Cart/Reorder | OrderReorderView добавляет позиции без color / color_id и с store=None; повтор заказа с цветными позициями теряет вариант и может слить линии | Medium | get_or_create(cart, product, store=None) без color | orders/views.py (~410–422) | нет | Передавать color (+ store) из OrderItem; учитывать UniqueConstraint cart+product+store+color | CONFIRMED |
| INT-027 | Bonus | При BONUS_ENABLED=False signal всё ещё может создавать пустой BonusAccount на регистрацию (без начислений) | Low | earlier gate only on award/spend | onus/signals.py | func007 covers awards | Опционально gated create; не блокер | CONFIRMED |
| INT-028 | Docs drift | В ранних секциях Stage2 ещё встречается формулировка про legacy phone+number; **текущий код** legacy full-access не даёт (SEC-006 FIXED). Исторические абзацы не переписывались по правилу аудита | Info | guest_access token-only vs старые абзацы ~1967/1993 | docs/audit/RINGO_FULL_AUDIT.md, orders/guest_access.py | sec006 | Читать актуальный статус FIXED в acceptance/Stage2 closeout, не устаревшие черновики | CONFIRMED |

Остальные выводы субагента (FUNC-001…005/007/009/011, SEC-001/002/006/007 = VERIFIED FIXED; promo validate-only; production blockers внешние) совпадают с матрицей Блока №4 и отдельных правок не требуют.

---

# БЛОК №5. ИСПРАВЛЕНИЕ НЕИСПРАВНОСТЕЙ INT-001–028

**Дата:** 2026-11-06  
**Режим:** доработка кода + тесты; commit/push/deploy/migrate staging|prod/реальные платежи — **нет**  
**Базовый HEAD:** `8a0bd5f814fa86e1f09404efb2a886ea1fe879da`  
**Предыдущие блоки №1–4 не переписывались** (кроме точечных INT-028 пометок в SEC-006).

## Сводная таблица

| ID | Исходная проблема | Исправление | Файлы | Тесты | Статус |
|---|---|---|---|---|---|
| INT-001 | Admin bulk confirm обходит FSM | Bulk confirm через `transition_order_status` поштучно; отчёт ok/skipped | `orders/admin.py`, `orders/services/transitions.py` | `test_int001_int002_order_fsm.py` | FIXED |
| INT-002 | Admin save_model свободная смена статуса | Любая смена статуса через FSM | `orders/admin.py`, `admin_api/views/orders.py` | FSM + admin_api paths | FIXED |
| INT-003 | Refund flow / paid cancel | Не реализован (бизнес); paid cancel по-прежнему запрещён | — | paid cancel tests | NEEDS BUSINESS DECISION |
| INT-004 | refund.succeeded → не refunded | GET `/refunds/{id}`; full match → REFUNDED; partial → needs_review; order не трогаем | `yookassa_service.py`, client `get_refund`, mig 0003 | `test_int004_int005_*` | FIXED |
| INT-005 | Пустые metadata → PAID | Обязательные order_id+payment_id; mismatch → needs_review | `yookassa_service.py` | `test_int004_int005_*`, sec007/yk updated | FIXED |
| INT-006 | Late payment / expire race | Expire не трогает NEEDS_REVIEW; revive только system override; late policy manual default | `payments/services.py`, transitions | func001 updated | PARTIALLY FIXED (PG concurrency NOT TESTED) |
| INT-007 | Нет lock на expire | Cache lease `task_lock` на expire/reconcile Celery tasks | `payments/locks.py`, `tasks.py`, settings TTL | `test_int007_expire_lock.py` | FIXED (unit); dual-beat на PG NOT TESTED |
| INT-008 | PG concurrency | Не запускалось — нет PG в среде | — | 6 skipped | BLOCKED / NOT TESTED |
| INT-009 | Нет журнала резервов | `StockMovement` + idempotent release/reserve ledger | `stores/models.py`, `ledger.py`, mig 0007, onec/orders.py | `test_int009_stock_ledger.py` | FIXED (release/revive paths) |
| INT-015 | needs_review как failed UI | Отдельный нейтральный блок на return page | `payment/return/page.tsx` | return page.test 8 passed | FIXED |
| INT-025 | Dirty tree release risk | Документ readiness без commit | `docs/audit/RELEASE_READINESS.md` | n/a | FIXED (docs only) |
| INT-026 | Reorder теряет color/store | Reorder с color+store, актуальная цена, skipped[] | `orders/views.py`, FE orders.service + pages | `test_int026_*` | FIXED |
| INT-027 | BonusAccount при BONUS off | Signal create gated by BONUS_ENABLED | `bonus/signals.py` | `test_int027_*` | FIXED |
| INT-028 | Устаревшие абзацы guest legacy | Пометки актуального состояния в SEC-006 | `RINGO_FULL_AUDIT.md` | sec006 suite | FIXED |

## Детали по ключевым INT

### INT-004
Webhook `refund.succeeded` больше не ищет Payment по refund id как по payment id. Выполняется `get_refund` → проверка payment_id/суммы/валюты/status → `STATUS_REFUNDED` + `yookassa_refund_id` (unique). Повтор — idempotent. Частичный возврат → `needs_review` без правил авто-возврата заказа.

### INT-005
Succeeded без metadata / с пустыми / неверными id → `needs_review` (не PAID). Expire не отменяет заказы с NEEDS_REVIEW.

### INT-001/002
`transition_order_status` — единая карта переходов; cancel делегирует в `cancel_order_and_release_stock`. Admin API PATCH и Django Admin используют сервис. System revive late-payment — `allow_system_override=True`.

### INT-006/007
Lock через `cache.add` TTL; HTTP к провайдеру по-прежнему вне длительной блокировки строки (как раньше). Полный dual-worker/PG race — NOT TESTED.

### INT-009
Журнал с unique `idempotency_key`; повторный release той же позиции — no-op. Не покрывает все сетевые release_across_stores пути целиком — частично через order item release.

### Миграции (созданы)
- `payments/0003_payment_yookassa_refund_fields`
- `stores/0007_stockmovement`  
Применение на staging/prod — вручную после бэкапа.

### Env (новые имена)
`PAYMENTS_EXPIRE_LOCK_TTL_SECONDS`, `PAYMENTS_RECONCILE_LOCK_TTL_SECONDS`.

## Регрессия

```
Backend pytest: 306 passed, 6 skipped
(target INT/SEC/FUNC ранее зелёные; concurrency_postgres skipped)
Frontend targeted return+orders tests: 8 passed
Vitest full / next build: см. финальный отчёт запуска
```

## Остаточные риски
- Реальные YooKassa/Sber/1С/VPS/SMTP/backup drill — NOT TESTED  
- Полный refund product — NEEDS BUSINESS DECISION  
- Promo apply — NEEDS BUSINESS DECISION  
- 1С color mapping — NEEDS BUSINESS DECISION  
- Stock ledger не на всех низкоуровневых Stock.* путях  
- Dirty working tree по-прежнему требует ручной сборки релиза (INT-025 doc)


---

# ДОПОЛНЕНИЕ. ЗАКРЫТИЕ ОСТАТКОВ БЛОКА №4 (после Блока №5)

**Дата:** 2026-11-06  
**Режим:** доработка + изолированные проверки на Docker PostgreSQL (
ingoo_db), без touch рабочей БД 
ingoo, без commit/push/deploy.

## Результаты по пунктам владельца

| # | Тема | Статус | Доказательство |
|---|---|---|---|
| 1 | PostgreSQL concurrency платежей/заказов | **VERIFIED** | 	ests/test_concurrency_postgres.py → **7 passed** на 
ingoo_concurrency_test (Sber×3, YK parallel+expire race, stock×2) |
| 2 | Полный журнал StockMovement | **FIXED** (основные пути) | stock_ops.py: checkout reserve, cancel release, revive, delivery net, admin correction, 1C upsert; тесты 	est_int009_* |
| 3 | Миграции 0008–0010 / 0002–0003 / 0007 | **VERIFIED** на чистой БД | 
ingoo_mig_check migrate OK, conflicts {}; dump→
ingoo_mig_seed + legacy Order/Payment/Stock OK |
| 4 | Регрессия | **VERIFIED** | Backend **310 passed, 8 skipped** (skip = concurrency без флага в default suite) |
| 5 | Backup restore | **PARTIALLY VERIFIED** | Local dump/restore drill VERIFIED; offsite/age на VPS — NOT VERIFIED |
| 6 | Мониторинг | **FIXED** (инструменты) | 
eport_ops_alerts, OPS_HEALTH_DETAILS в /health/, docs/ops/MONITORING_OPS_ALERTS.md; внешний pager — NOT WIRED |

## Бизнес-вопросы (без изменений)

Возвраты / цвета↔1С / промокоды — по-прежнему **NEEDS BUSINESS DECISION**.

## Новые артефакты

- ackend/apps/stores/stock_ops.py
- ackend/apps/payments/management/commands/report_ops_alerts.py
- ackend/tests/test_int009_stock_ledger_complete.py (+ YK concurrency в 	est_concurrency_postgres.py)
- docs/ops/MONITORING_OPS_ALERTS.md
- обновлён docs/ops/BACKUP_AND_RESTORE.md

## Команда PG concurrency (повтор)

`
set RINGOO_TEST_POSTGRES=1
set DATABASE_URL=postgresql://USER:PASS@127.0.0.1:5436/ringoo_concurrency_test
set DJANGO_SETTINGS_MODULE=config.settings.test_postgres
pytest tests/test_concurrency_postgres.py -q --no-cov
`

## Вердикт

Технические пункты 1–4 по остаткам блока №4 **можно считать закрытыми** в рамках изолированных проверок.  
Пункты 5 (offsite) и внешний alerting, а также live YooKassa/1С/VPS — отдельный эксплуатационный/стендовый этап.


---

# ФИНАЛЬНОЕ ДОПОЛНЕНИЕ. ЗАКРЫТИЕ ОСТАТКОВ БЛОКА №4

**Дата:** 2026-11-06  
**Режим:** реализация admin backup + спецификации + локальный commit; без push/deploy/production migrate/реальных платежей и 1С write.

## Сводка статусов

| Тема | Статус | Комментарий |
|---|---|---|
| Резервное копирование (админ UI) | **FIXED** | Раздел /admin/backup, кнопка создания и скачивания |
| Скачивание архива на компьютер | **FIXED** | Auth + временный download_token, TTL |
| Состав архива (DB+media+manifest+checksums+guide) | **FIXED** | pps.backups; без .env/секретов |
| Шифрование паролем (AES-256-GCM / Scrypt) | **FIXED** | Пароль не сохраняется на сервере |
| Тест восстановления | **VERIFIED** (изолированный) | 	est_restore_drill_extract_media_and_db |
| Offsite / облако | **NOT IMPLEMENTED** | Только ручное хранение на SSD; без S3 |
| Мониторинг ops + backup stale/failed | **FIXED** | 
eport_ops_alerts, /health ops |
| Внешний канал уведомлений | **PARTIAL** | EXTERNAL_MONITORING_SETUP.md; секреты не подключены |
| Складские возвраты (после выдачи) | **NEEDS BUSINESS DECISION** | Spec в REFUND doc; авто-restock не внедрён |
| Денежные возвраты (полный YK webhook) | **FIXED** (INT-004 ранее) | Инициация refund админом не сделана |
| Денежные частичные / admin initiate | **NEEDS BUSINESS DECISION** | См. spec |
| Цвета на сайте (OrderItem/reorder) | **FIXED** (ранее) | |
| Цвет ↔ 1С mapping | **NEEDS BUSINESS DECISION** | ONEC_COLOR_MAPPING_SPEC.md |
| Git локальный commit | **VERIFIED** | 651994bd9ce7b89ced3fcaa78cf120216c5f8e78 (267 files), без push |
| Промокоды | **NOT IMPLEMENTED** | Исключены из задачи |

## Резервное копирование

- Backend: pps/backups, URLs /api/v1/admin/backups/*, только **superuser + Admin MFA** (если OTP включён).
- Frontend: отдельный раздел меню «Резервное копирование».
- Документы: docs/ops/BACKUP_RESTORE_GUIDE.md.
- Защита: create-lock, path traversal block, token hash, expire, audit без PII/пароля.
- Тесты: pps/backups/tests.py — **8 passed**.

## Мониторинг

- ackup_failed_24h, ackup_stale в 
eport_ops_alerts.
- Health ops: ackup_latest_ready_at, ackup_failed_24h.
- docs/ops/EXTERNAL_MONITORING_SETUP.md.

## Возвраты и 1С

- docs/audit/REFUND_BUSINESS_AND_TECHNICAL_SPEC.md
- docs/audit/ONEC_COLOR_MAPPING_SPEC.md

## Тестирование (этот этап)

| Набор | Результат |
|---|---|
| pps.backups.tests | **8 passed** |
| SEC-001…009 | **80 passed** |
| FUNC/INT004 набор | **40 passed** |
| YK/Sber/payment/repay/cart | **101 passed** |
| pps tests integrations | **522 passed, 9 skipped** |
| PG concurrency (
ingoo_concurrency_test) | **7 passed** |
| Frontend Vitest | **90 passed** (34 files) |
| 	sc --noEmit | **exit 0** |
| 
ext build | **exit 0** |

## Git

- Старый HEAD: 8a0bd5f814fa86e1f09404efb2a886ea1fe879da
- Новый HEAD: 651994bd9ce7b89ced3fcaa78cf120216c5f8e78
- Сообщение: ix: complete security, functional and integration audit remediations
- Исключено из commit: copy-site/, integration1CandKassa/, бинарные .docx, Описание работ.txt, локальные .env
- Working tree: остались только исключённые/локальные файлы

## Ограничения

- Авто-offsite и Telegram notify требуют секретов владельца.
- Без pg_dump возможен fallback на dumpdata (поле warning в manifest).
- Возвраты товара/частичные деньги и маппинг цвета 1С — ждут бизнес-решений.
- Production VPS / live API не трогались.
