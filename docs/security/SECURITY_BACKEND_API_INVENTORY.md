# Инвентаризация Backend API

Дата: 2026-11-07. Источник — маршруты в коде, не старые документы. Код приложения не менялся. Запросы на `test.ringoo15.store` не отправлялись.

Префикс REST: `/api/v1/`. Django Admin: `/{DJANGO_ADMIN_URL}/`, в коде по умолчанию `admin/`, если переменная пустая или не проходит шаблон. Живое значение на сервере не читалось.

Общий шлюз admin API (`admin_permissions`): `IsAuthenticated` + `IsStaff` + `AdminMfaVerified` + группа. `AdminMfaVerified` пропускает всех, пока `ADMIN_OTP_ENABLED` выключен. В модуле production OTP обязателен. Суперпользователь проходит проверку группы, не проверку staff и не MFA: staff и MFA для него тоже нужны, группа — да, суперпользователь её заменяет.

Динамика этого блока: изолированный прогон `config.settings.test` (SQLite в памяти). Рабочая PostgreSQL не открывалась. Прогнанные вызовы отмечены в колонке риска словом «SQLite». Остальное — разбор кода.

## Служебные маршруты вне `/api/v1/`

| Endpoint | Метод | View | Auth | Permission | Роль | Владение | Вход | Выход | Эффект | Риск |
|---|---|---|---|---|---|---|---|---|---|---|
| `/health/` | GET | `health_check` | нет | нет | все | нет | нет | `ok` плюс ping БД и кэша. Счётчики только при `OPS_HEALTH_DETAILS` | чтение | низкий, если флаг выключен |
| `/` | GET | redirect | нет | нет | все | нет | нет | на `/health/` или на `/api/docs/`, если `DEBUG` или `API_DOCS_PUBLIC` | нет | низкий |
| `/api/schema/`, `/api/docs/`, `/api/redoc/` | GET | spectacular | нет | только если docs включены | все | нет | нет | схема API | нет | средний в production, если флаг включён |
| `/media/<path>` | GET | django static serve | нет | только при `SERVE_MEDIA` вне DEBUG | все | нет | путь файла | файл из `MEDIA_ROOT` | чтение файла | средний, если каталог публичный и в нём лежат не только картинки витрины |
| `/{DJANGO_ADMIN_URL}/` | * | Django Admin, при OTP — `OTPAdminSite` | сессия | `is_staff`, в production ещё TOTP | staff / superuser | ModelAdmin | формы | модели, экспорт CSV заказов | запись в модели | высокий по данным. Живой URL не запрашивался |
| `/__debug__/` | * | debug toolbar | нет | только `DEBUG` | все в dev | нет | нет | панель | нет | не для production |

## Аутентификация `/api/v1/auth/`

Сериализаторы: `UserSerializer` (все поля read-only, нет `is_staff`), `MarketingOptInSerializer` (одно поле), `RegisterSerializer` (телефон, пароль, ФИО, согласия).

| Endpoint | Метод | View | Auth | Permission | Роль | Владение | Вход | Выход | Эффект | Риск |
|---|---|---|---|---|---|---|---|---|---|---|
| `/auth/token/` | POST | `TokenObtainPairViewNoCSRF` | нет | AllowAny, axes, throttle `auth_login` 5/min | все | свой пароль | телефон, пароль | access/refresh или cookies, если `X-Auth-Cookies: 1` | сессия | высокий при слабом пароле. CSRF на этом view снят |
| `/auth/token/refresh/` | POST | `CookieTokenRefreshView` | refresh | AllowAny, rotation и blacklist | владелец refresh | refresh | новая пара | старый refresh в blacklist | средний |
| `/auth/logout/` | POST | `LogoutView` | нет | AllowAny | все | refresh из тела или cookie | `{detail}` | blacklist refresh, сброс cookie. Access не отзывается | низкий остаток до exp access |
| `/auth/register/` | POST | `RegisterView` | нет | AllowAny, `auth_register` 5/hour | аноним | телефон, пароль, согласия | пользователь без `is_staff` | создаёт пользователя | низкий для повышения прав |
| `/auth/password-reset/` | POST | `PasswordResetRequestView` | нет | throttle 5/hour | все | email | одинаковый текст | письмо, ссылка из `FRONTEND_URL` | низкий перебор |
| `/auth/password-reset/confirm/` | POST | `PasswordResetConfirmView` | нет | throttle 10/hour | держатель токена | uid, token, пароль | успех | смена пароля, blacklist refresh пользователя | средний |
| `/auth/me/` | GET | `UserMeView` | JWT | IsAuthenticated | свой аккаунт | нет | профиль, телефон, email. Нет `is_staff` | чтение | низкий. SQLite: ключа `is_staff` нет |
| `/auth/me/` | PATCH | `UserMeView` | JWT | IsAuthenticated | свой аккаунт | только `marketing_opt_in` | те же поля профиля | пишет два поля согласия | низкий. SQLite: `is_staff: true` в теле не изменил флаг |
| `/auth/me/export/` | GET | `UserDataExportView` | JWT | IsAuthenticated | свой аккаунт | нет | выгрузка своих данных | чтение | низкий |
| `/auth/staff-access/` | GET | `StaffAccessView` | JWT | IsAuthenticated | staff | нет | 403 иначе; 200: staff, groups, superuser, mfa | чтение | низкий |
| `/auth/mfa/status/` | GET | `AdminMfaStatusView` | JWT | IsAuthenticated | свой | нет | флаги OTP без секрета | чтение | низкий |
| `/auth/mfa/verify/` | POST | `AdminMfaVerifyView` | JWT | staff, throttle 5/min | staff | код TOTP | новые JWT с `admin_mfa` | выдаёт claim | высокий при слабом коде. Разбор TOTP — блок 5 |
| `/auth/delete-account/` | POST | `DeleteAccountView` | JWT | IsAuthenticated | свой | пароль | успех | `is_active=False`, анонимизация | средний |
| `/auth/addresses/` | GET, POST | `DeliveryAddressListCreateView` | JWT | IsAuthenticated | свой | queryset `user=request.user` | свои адреса | создаёт адрес себе | низкий |
| `/auth/addresses/{id}/` | GET, PATCH, PUT, DELETE | `DeliveryAddressDetailView` | JWT | IsAuthenticated | свой | тот же queryset | свой адрес | правка и удаление | низкий |
| `/legal/analytics-consent/` | POST | `AnalyticsConsentView` | нет | throttle | все | флаг согласия | запись согласия | запись | низкий |

## Каталог и магазины, чтение

Публичные view каталога — `AllowAny`, только GET. Сортировка товара — белый список (`price_asc`, `price_desc`, `rating_desc`, `popular`, иначе дата). Запись названия, цены, SEO, картинок — только admin API группы `ringoo_catalog` или `ringoo_stores` и задачи 1С.

| Endpoint | Метод | View | Serializer | Auth | Вход | Выход | Эффект | Риск |
|---|---|---|---|---|---|---|---|---|
| `/products/categories/` | GET | `CategoryViewSet.list` | список категорий | нет | фильтры | активные категории | чтение | низкий |
| `/products/categories/{id}/` | GET | retrieve | категория | нет | uuid | категория | чтение | низкий |
| `/products/products/` | GET | `ProductListView` | `ProductListSerializer` | нет | фильтры, `ordering` из списка | активные товары | чтение | низкий |
| `/products/products/brands/` | GET | `ProductBrandsListView` | — | нет | фильтры | бренды | чтение | низкий |
| `/products/products/product-models/` | GET | `ProductModelsListView` | — | нет | фильтры | линейки | чтение | низкий |
| `/products/products/autocomplete/` | GET | `ProductAutocompleteView` | — | нет | `q` | подсказки | чтение | низкий |
| `/products/products/{slug}/` | GET | `ProductDetailView` | detail | нет | slug | карточка, описание, SEO | чтение | источник данных FE-002, сама запись закрыта |
| `/products/products/{id}/stock/` | GET | `ProductStockView` | — | нет | uuid | остатки по магазинам | чтение | низкий |
| `/stores/` | GET | `StoreListView` | список | нет | — | магазины | чтение | низкий |
| `/stores/{id}/` | GET | `StoreDetailView` | `StorePageSerializer` | нет | uuid | телефон, email, описание, SEO магазина | чтение | низкий. Это контакты точки, не логин сотрудника |
| `/stores/{id}/stock/` | GET | `StockListView` | — | нет | uuid | остатки | чтение | низкий |
| `/stores/by-slug/{slug}/` | GET | `StoreBySlugView` | страница | нет | slug | то же | чтение | низкий |
| `/stores/by-slug/{slug}/products/` | GET | `StoreProductsBySlugView` | товары | нет | slug | товары точки | чтение | низкий |
| `/stores/managers/` | GET | `ManagerListView` | краткий | нет | — | имя, должность, фото, рейтинг | чтение | низкий |
| `/stores/managers/by-slug/{slug}/` | GET | `ManagerDetailBySlugView` | `ManagerDetailSerializer` | нет | slug | публичная карточка без личного телефона | чтение | низкий |
| `/stores/managers/by-slug/{slug}/reviews/` | GET | `ManagerReviewsBySlugView` | отзывы | нет | slug | отзывы без данных заказа | чтение | низкий |

## Корзина, избранное, контент, CRM, акции

| Endpoint | Метод | View | Auth | Владение | Вход | Выход | Эффект | Риск |
|---|---|---|---|---|---|---|---|---|
| `/cart/` | GET | `CartView` | нет | корзина сессии или пользователя | нет | свои позиции | создаёт пустую корзину | низкий |
| `/cart/items/` | POST | `CartItemCreateView` | нет | своя корзина | product, qty, store, color | корзина | проверка остатка, если указан магазин | низкий |
| `/cart/items/{id}/` | PATCH, DELETE | `CartItemDetailView` | нет | `pk` и `cart` текущей корзины | qty | корзина | чужой id → 404 | низкий |
| `/cart/clear/` | POST | `CartClearView` | нет | своя корзина | нет | пусто | чистит свою | низкий |
| `/wishlist/` | GET | `WishlistListView` | JWT | `user=request.user` | нет | свои товары | чтение | низкий |
| `/wishlist/{product_id}/` | POST, DELETE | `WishlistItemDetailView` | JWT | свой | product id | элемент | добавление и удаление своего | низкий |
| `/content/tags/` | GET | `TagViewSet` | нет | нет | — | теги | чтение | низкий |
| `/content/articles/` | GET | `ArticleViewSet` | нет | нет | `is_published`, search, tag | список. Черновики при `is_published=false` | чтение | RINGOO-API-002 |
| `/content/articles/{slug}/` | GET | тот же | нет | нет | slug | `content`, `author_phone` | чтение | RINGOO-API-001, API-002 |
| `/content/news/` и `/{slug}/` | GET | `NewsViewSet` | нет | нет | те же | те же поля новости | чтение | те же находки |
| `/content/reviews/` | GET | `ReviewViewSet` | нет | нет | — | только `is_approved=True`, без email | чтение | низкий |
| `/content/reviews/` | POST | create | нет | нет | текст, имя, email | созданный отзыв, email не в публичном чтении | запись на модерацию | низкий. HTML в отзыве на витрине не рендерится как HTML |
| `/content/page-gallery/` | GET | `PageGalleryListView` | нет | нет | — | картинки страниц | чтение | низкий |
| `/crm/missing-product/` | POST | `MissingProductRequestCreateView` | нет | нет | имя, телефон, email, текст, согласия | эхо своей заявки и id | создаёт заявку, ставит задачу письма | низкий. Списка чужих заявок нет |
| `/promotions/` | GET | `PromotionListView` | нет | нет | — | опубликованные акции | чтение | низкий |
| `/promocodes/validate/` | POST | `PromoCodeValidateView` | см. view | нет создания скидки в заказе этим вызовом | код | годность кода | чтение | низкий. Скидка заказа этим блоком не подтверждена как применённая: в создании заказа итог считается с каталога |

Бонусы `/api/v1/bonus/` в `api_urls.py` закомментированы. Файл `apps/bonus/urls.py` существует и в HTTP не подключён.

## Заказы и оплата

| Endpoint | Метод | View | Auth | Владение | Вход | Выход | Эффект | Риск |
|---|---|---|---|---|---|---|---|---|
| `/orders/` | GET | `OrderListCreateView` | JWT | `user=request.user` | нет | свои заказы | чтение | низкий. SQLite: список A пуст при заказе B |
| `/orders/` | POST | тот же | нет | владелец = `request.user` или пусто | состав, контакты, адрес JSON, тип оплаты. `user_id` нет | свой заказ | цена с каталога, доставка 0, бонус 0 | низкий для подмены суммы. Создание на SQLite не вызывалось |
| `/orders/{id}/` | GET | `OrderDetailView` | JWT | queryset по user | uuid | свой заказ, контакты, адрес, позиции | чтение | низкий. SQLite: чужой id → 404 |
| `/orders/{id}/reorder/` | POST | `OrderReorderView` | JWT | `pk` и user | нет | корзина | кладёт свои позиции по актуальной цене | низкий |
| `/orders/{id}/cancel/` | POST | `OrderCancelView` | владелец или guest token | не staff-bypass | нет | статус | только `new`/`confirmed`, оплаченный нельзя | низкий |
| `/orders/{id}/pay/` | POST | `OrderPayView` | AllowAny, но `_can_access_order` | владелец или guest token. Staff чужой не открывает | нет суммы | `form_url` | сумма из `Order.total_amount`. ЮKassa не вызывалась | низкий для чужой оплаты по коду |
| `/orders/{id}/payment/` | GET | `OrderPaymentStatusView` | то же | то же | нет | статус своего платежа | чтение и сверка | низкий |
| `/orders/track/`, `/orders/status/` | GET/POST | track/status | нет | номер + телефон, либо guest token | телефон, номер | без токена: статус, тип оплаты и доставки, дата. С токеном: полный заказ | чтение | ограниченный оракул статуса, 5/min. Не полный заказ |
| `/orders/rate/` | POST | `OrderRateView` | владелец или token | свой заказ | оценка | оценка | запись оценки | низкий |
| `/orders/ratings-summary/` | GET | summary | нет | нет | — | агрегаты | чтение | низкий |
| `/orders/guest-access/recover/` | POST | recover | нет | email заказа | email, номер | одинаковый текст | письмо со ссылкой из `FRONTEND_URL` | низкий |
| `/orders/guest-access/recover/confirm/` | POST | confirm | нет | код из письма | код | новый guest token | выдаёт токен | средний |
| `/payments/sber/callback/` | POST | `SberCallbackView` | нет | пустые authentication classes | тело банка | статус | не доказательство оплаты само по себе. Разбор — блок 8 | не закрыт в этом блоке |
| `/payments/yookassa/webhook/` | POST | `YooKassaWebhookView` | нет | IP allowlist по `REMOTE_ADDR`, если список задан | тело | 200 | повторный GET в ЮKassa. Не вызывался | блок 8 |
| `/returns/` | GET | `CustomerReturnListView` | JWT | `user=request.user` | нет | свои, если флаг включён | иначе 403 `returns_temporarily_disabled` | низкий |
| `/returns/create/` | POST | `CustomerReturnCreateView` | JWT | владелец заказа, плюс любой staff | `order_id`, позиции | возврат | флаг по умолчанию выключен | RINGOO-API-003 при включении |
| `/returns/{id}/` | GET | `CustomerReturnDetailView` | JWT | владелец или любой staff | uuid | возврат | тот же флаг | RINGOO-API-003 |

## Admin API `/api/v1/admin/`

Все строки ниже: JWT, `is_staff`, MFA если OTP включён. Обычный пользователь на SQLite получил 403 на `GET /admin/orders/`. Группа чужого контура по коду не проходит `HasAdminGroupPermission`. Динамически матрица групп не гонялась (блок 5).

| Endpoint | Методы | Группа | Эффект | Риск |
|---|---|---|---|---|
| `/admin/dashboard/stats/` | GET | любая `ringoo_*` или superuser | сводка | средний, PII в агрегатах |
| `/admin/onec/sync/status/`, `/logs/`, `/logs/{id}/`, `/probe/`, `/dry-run/` | GET/POST | `ringoo_catalog` | чтение 1С и пробный разбор | высокий: данные каталога и ответ 1С |
| `/admin/onec/sync/apply/` | POST | `ringoo_catalog` | применяет синхронизацию | высокий. В 1С из этого блока не ходили |
| `/admin/orders/`, `/orders/{id}/` | GET, PATCH | `ringoo_orders` | список всех заказов. PATCH только `status` через FSM | высокий по PII. В `paid` клиентским полем не переводится: статуса paid в FSM нет |
| `/admin/orders/export/` | GET | `ringoo_orders` | CSV заказов | высокий |
| `/admin/products/`, `/create/`, `/{id}/`, `/{id}/patch/` | GET, POST, PATCH | `ringoo_catalog` | название, бренд, описание, SEO, цена, sku, категория, публикация. `onec_code` read-only. Поля 1С у связанного товара отклоняются | высокий. Это запись для FE-002 |
| `/admin/products/{id}/images/`, `/images/{id}/`, `/specs/` | GET, POST, PATCH, DELETE | `ringoo_catalog` | картинки и характеристики | средний. Имя файла заменяется на uuid |
| `/admin/products/bulk/set-active/`, `/bulk/update-prices/` | POST | `ringoo_catalog` | публикация и цены пачкой | высокий |
| `/admin/products/export/`, `/import/`, `/import/template/` | GET, POST | `ringoo_catalog` | CSV/XLSX | высокий. Разбор файла — блок 10 |
| `/admin/products/color-mappings/` | GET, PATCH | `ringoo_catalog` | соответствие цветов | низкий |
| `/admin/products/categories/`, `/create/`, `/{id}/patch/` | GET, POST, PATCH | `ringoo_catalog` | имя и SEO категории | высокий для FE-002 |
| `/admin/stores/`, `/create/`, `/{id}/patch/`, images | GET, POST, PATCH, DELETE | `ringoo_stores` | название, описание, контакты, картинки точки | высокий для JSON-LD магазина |
| `/admin/stores/stock/` и срезы by-store | GET, PATCH | `ringoo_stores` | остатки | высокий |
| `/admin/managers/` | GET, POST, PATCH, DELETE | `ringoo_stores` | карточки менеджеров | средний |
| `/admin/users/`, `/{id}/`, `/{id}/patch/` | GET, PATCH | `ringoo_users` | телефоны, email, адреса, группы. PATCH: `is_active` любой из группы, `is_staff` и `groups` только superuser | RINGOO-AUTH-001 |
| `/admin/content/tags|articles|news|reviews|page-gallery/` | GET, POST, PATCH, DELETE | `ringoo_content` | тексты, в том числе HTML статьи | высокий, если витрина начнёт рендерить HTML. Сейчас витрина новостей — заглушка |
| `/admin/promotions/`, `/promocodes/` | GET, POST, PATCH, DELETE | `ringoo_catalog` | акции и коды | средний |
| `/admin/crm/requests/` | GET, PATCH | `ringoo_crm` | заявки с телефонами | высокий по PII |
| `/admin/reports/revenue|orders|top-products/` | GET | `ringoo_reports` | агрегаты | средний |
| `/admin/returns/` и transition, refund, inspect | GET, POST | `ringoo_orders` | возвраты, деньги, склад | высокий. Флаг возвратов по умолчанию выключен |
| `/admin/backups/create|latest|{id}|download/` | POST, GET | суперпользователь (`IsSuperuserBackupAdmin`) | дамп и скачивание | критичный по данным. Не скачивался. Блок 10 |
| `/admin/backups/offsite/*` | GET, POST | суперпользователь | выгрузка наружу | критичный. Не вызывался |

Закомментированные `/admin/bonus/` в urls не смонтированы.

## Что не является маршрутом

- Публичный bonus API закомментирован.
- Входящего HTTP от 1С нет. Клиент 1С ходит наружу по `ONE_C_API_BASE_URL`.
- Отдельного endpoint смены роли у покупателя нет.
- `debug_task` Celery в HTTP не опубликован.
