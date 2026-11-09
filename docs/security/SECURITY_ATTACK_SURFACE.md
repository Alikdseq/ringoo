# Поверхность атаки Ringoo

- Дата: 2026-11-07
- Основа: URL-конфигурация и `permission_classes` в коде. Это перечень точек входа, не результаты эксплуатации.
- Префикс API: `/api/v1/`.
- Права «наследуют DRF» означают класс по умолчанию `IsAuthenticatedOrReadOnly`, если view не задаёт свой.
- Живой хост `test.ringoo15.store` не сканировался. Статус сетевой экспозиции: **НЕ ПРОВЕРЕНО**.

## 1. Внешние точки входа

| Точка | Кто достучится по задумке деплоя | Доверие |
|---|---|---|
| HTTPS → Nginx → Next.js `:3000` | интернет | недоверенный ввод |
| Next rewrite `/api/v1`, `/media` → Django | браузер через тот же origin | заголовки клиента проксируются |
| Django `:8000` напрямую | в prod overlay только `127.0.0.1`; в dev — хост | обход Next-гейта |
| Django Admin `/{DJANGO_ADMIN_URL}/` | тот, кто знает префикс | сессия + OTP в production settings |
| `GET /health/` | без аутентификации | утечка факта живости БД/Redis и, при флаге, ops-счётчиков |
| `/api/docs/`, `/api/schema/`, `/api/redoc/` | только `DEBUG` или `API_DOCS_PUBLIC` | схема всех маршрутов |
| `POST /api/v1/payments/yookassa/webhook/` | интернет, если маршрут опубликован | не доказательство оплаты |
| `POST /api/v1/payments/sber/callback/` | интернет, если Сбер включён | общий секрет + сверка у банка |
| Исходящие: ЮKassa, Сбер, 1С, SMTP, S3, Яндекс | процесс Django/Celery | секреты из env |
| PostgreSQL `:5432`, Redis `:6379` | в prod overlay порты не публикуются; в dev публикуются | пароль; в dev дефолты слабые |
| Загрузка файлов admin API и аватар | staff / владелец профиля | содержимое файла |
| Скачивание backup | staff backup API | полный дамп |

Отдельного входящего маршрута 1С в Django нет. Поверхность 1С — исходящий клиент и админские кнопки запуска.

## 2. Публичные маршруты приложения (не API)

Доступны без JWT, если не перечислены в `frontend/src/proxy.ts`.

Без cookie-гейта: `/`, каталог, карточка товара, корзина, избранное (UI; API избранного требует JWT), checkout, login, register, forgot/reset password, магазины, сотрудники, акции, новости, блог, рассрочка, о компании, юридические страницы, карта сайта, `/order-status`, `/order-rate`, `/admin/login`, страницы успеха и возврата с оплаты (`/orders/success`, `/orders/{id}/success`, `/orders/{id}/payment/return|fail`).

С cookie-гейтом только при `authCookiesMode()` (production по умолчанию): `/profile/*`, `/orders` и `/orders/*` кроме публичных веток выше, `/admin/*` кроме login. Гейт смотрит на наличие cookie, не на роль и не на подпись JWT.

При `NEXT_PUBLIC_USE_AUTH_COOKIES=0` функция `proxy` после API/media rewrite сразу вызывает `NextResponse.next()` — страницы профиля и админки на edge не закрываются.

## 3. Публичное API (AllowAny или анонимное чтение)

Метод указан по view. Чтение каталога дополнительно throttle `anon_read` / `user_read`, где задано.

| Метод и путь | Назначение | Примечание для аудита |
|---|---|---|
| `POST /auth/token/` | вход по телефону | axes + throttle `auth_login` 5/min; CSRF exempt |
| `POST /auth/token/refresh/` | новый access | ротация и blacklist |
| `POST /auth/register/` | регистрация | throttle 5/hour |
| `POST /auth/password-reset/` | запрос сброса | throttle 5/hour; ответ не должен различать номера |
| `POST /auth/password-reset/confirm/` | установка пароля | throttle 10/hour |
| `POST /auth/logout/` | blacklist | см. BLOCK 5: нужен ли refresh без auth |
| `GET /products/categories/`, `GET .../{uuid}/` | категории | публичное чтение |
| `GET /products/products/`, brands, product-models, autocomplete, `/{slug}/` | каталог и поиск | фильтры, сортировка, инъекции |
| `GET /products/products/{uuid}/stock/` | остатки товара | объём раскрытия складов |
| `GET /stores/`, `/{uuid}/`, by-slug, products, stock, managers | магазины и менеджеры | PII сотрудников |
| `GET/POST /cart/`, items, clear | корзина | гостевая корзина, подмена id позиции |
| `POST /orders/` | создание заказа | цена и количество с клиента |
| `POST /orders/track/`, `POST /orders/status/` | статус по номеру и телефону | оракул и перебор |
| `POST /orders/rate/` | оценка | привязка к чужому заказу |
| `GET /orders/ratings-summary/` | сводка оценок | агрегаты менеджеров |
| `POST /orders/guest-access/recover/` и `.../confirm/` | восстановление гостевого доступа | перебор и захват заказа |
| `POST /orders/{uuid}/pay/` | старт оплаты | AllowAny + проверка владельца/guest token |
| `GET /orders/{uuid}/payment/` | статус оплаты | то же |
| `POST /orders/{uuid}/cancel/` | отмена | класс AllowAny; объектная проверка обязательна |
| `GET /content/tags|articles|news|reviews|page-gallery/` | контент | HTML в полях |
| `POST /content/reviews/` | отзыв гостя | stored XSS, спам |
| `GET /promotions/` | акции | |
| `POST /promocodes/validate/` | промокод | оракул и перебор; флаг `PROMOCODES_ENABLED` |
| `POST /crm/missing-product/` | заявка | PII, спам |
| `POST /legal/analytics-consent/` | согласие аналитики | |
| `POST /payments/yookassa/webhook/` | webhook | AllowAny, auth classes пустые |
| `POST /payments/sber/callback/` | callback | то же |
| `GET /health/` | здоровье | без DRF |

Бонусный публичный API (`/bonus/`) в `config/api_urls.py` закомментирован. Код `apps/bonus/views.py` остаётся и требует `IsAuthenticated`, если маршрут включат.

## 4. API покупателя (JWT)

| Метод и путь | Объектная проверка, которую надо подтвердить |
|---|---|
| `GET/PATCH /auth/me/` | только свой пользователь; запрет смены `is_staff` |
| `GET /auth/me/export/` | только свои данные |
| `GET /auth/staff-access/` | не выдаёт права, только признак |
| `POST /auth/mfa/status/`, `POST /auth/mfa/verify/` | TOTP только для staff; throttle verify |
| `POST /auth/delete-account/` | только свой аккаунт |
| `GET/POST /auth/addresses/`, `PATCH/DELETE /auth/addresses/{int}/` | чужой адрес |
| `GET /orders/` | только свои |
| `GET /orders/{uuid}/` | IDOR |
| `POST /orders/{uuid}/reorder/` | IDOR |
| `GET/POST /wishlist/`, `DELETE /wishlist/{product_id}/` | только свои |
| `GET/POST /returns/`, `POST /returns/create/`, `GET /returns/{uuid}/` | флаг `RETURNS_ENABLED` и владелец |

`OrderListCreateView.get_permissions`: GET — `IsAuthenticated`, POST — `AllowAny`.

## 5. Админское API `/api/v1/admin/`

Общий каркас: `IsAuthenticated` + `IsStaff` + `AdminMfaVerified` + группа. Суперпользователь проходит любую группу. Если `ADMIN_OTP_ENABLED` выключен (development), `AdminMfaVerified` возвращает True.

| Группа | Операции |
|---|---|
| `ringoo_orders` | список и правка заказов, экспорт, возвраты (list, detail, transition, refund, inspect) |
| `ringoo_catalog` | товары, картинки, характеристики, массовые цены и активность, экспорт, XLSX-импорт (флаг), категории, цветовые соответствия, синхронизация 1С: status, logs, probe, dry-run, **apply** |
| `ringoo_stores` | магазины, картинки, остатки, менеджеры (создание и удаление) |
| `ringoo_content` | теги, статьи, новости, отзывы, галерея страниц |
| `ringoo_crm` | заявки «нет товара» |
| `ringoo_reports` | выручка, заказы, топ товаров |
| `ringoo_users` | список, карточка и правка пользователей |
| любая группа или superuser | `GET dashboard/stats/` |
| backup permissions | create, latest, status, **download**, offsite status/probe/upload/verify |

Точные классы backup — `BACKUP_PERMISSIONS` в `apps/backups/views.py` (staff + MFA; состав группы уточняется в BLOCK 5, не предполагается равным «любому staff»).

Опасные действия на этой поверхности: смена роли пользователя, apply каталога 1С, правка остатков и цен, экспорт заказов, скачивание бэкапа, refund.

Закомментированы и не смонтированы: `/admin/bonus/accounts/*`.

## 6. Django Admin

- Путь: `settings.ADMIN_SITE_URL_PATH`, по умолчанию `admin/`.
- При `ADMIN_OTP_ENABLED` класс сайта заменяется на `OTPAdminSite`.
- В production-модуле OTP нельзя выключить без падения импорта settings.
- Поверхность: все зарегистрированные `ModelAdmin`, включая пользователей, заказы, платежи, sync log, OTP devices.
- Обход витринной группы `ringoo_*`: кто имеет сессию Django Admin, действует правами Django (`is_staff` / permissions моделей), это отдельная модель доступа.

## 7. Загрузки файлов

| Место | Кто |
|---|---|
| `POST /api/v1/admin/products/{id}/images/` | `ringoo_catalog` |
| `POST /api/v1/admin/stores/{id}/images/` | `ringoo_stores` |
| `POST /api/v1/admin/content/page-gallery/create/` | `ringoo_content` |
| аватар профиля | владелец `UserProfile.avatar` |
| импорт XLSX `POST /api/v1/admin/products/import/` | `ringoo_catalog`, флаг `PRODUCT_XLSX_IMPORT_ENABLED` |
| медиа `GET /media/<path>` | публичная раздача Django в DEBUG; в production при `SERVE_MEDIA` (ветка Vercel); иначе ожидается отдельная раздача. Next проксирует `/media/` на backend |

Лимиты: `DATA_UPLOAD_MAX_MEMORY_SIZE` 10 МиБ, `FILE_UPLOAD_MAX_MEMORY_SIZE` 5 МиБ (переопределяются env). Проверка сигнатуры, SVG и path traversal — BLOCK 10.

## 8. Интеграции как поверхность

| Система | Направление | Секрет | Включено по умолчанию в коде |
|---|---|---|---|
| ЮKassa | исходящий API + входящий webhook | shop id, secret key | нет |
| Сбер ecom | исходящий API + входящий callback | username, password, callback token | нет |
| 1С `/razrab/hs` | только исходящий | Basic login/password | нет |
| SMTP | исходящий | пароль ящика | backend задан, креды пустые |
| S3 бэкапов | исходящий | access/secret | нет |
| Яндекс | исходящий геокодер; браузерные карты | ключ геокодера | ключ пустой |
| Sentry | браузер и сервер Next | DSN публичен по природе | если задан при сборке |
| Telegram ops | по документации | bot token | не подтверждён вызов в BLOCK 1 |

Подмена «успешной оплаты» с браузера — отдельная проверка: страницы return/fail не должны писать статус заказа.

## 9. Внутренние сервисы

Из контейнера в `ringoo_network` по DNS:

- `db:5432`
- `redis:6379`
- `web:8000`
- `frontend:3000` (исходящий смысл меньше)

Celery не публикует порт. Очередь доступна тому, кто говорит с Redis. Имена задач, которые стоит считать привилегированными: catalog sync apply, order sync/cancel в 1С, backup create/upload/retention, expire/reconcile платежей, partner sync.

`debug_task` и `test_celery_task` существуют в коде. Их внешний HTTP-вызов в BLOCK 1 не найден.

## 10. Потенциальные утечки (кандидаты, не находки)

| Канал | Что может утечь | Где смотреть дальше |
|---|---|---|
| JSON login/refresh без заголовка `X-Auth-Cookies` | access и refresh в теле | BLOCK 3 и 5 |
| `localStorage` при cookie mode off | JWT доступен любому JS страницы | BLOCK 3 |
| `sessionStorage` guest token | доступ к заказу в этой вкладке | BLOCK 5 и 8 |
| Ответы `PaymentSerializer` | `form_url`, id шлюза, фрагменты ответа банка | BLOCK 8 |
| `Order` serializer для гостя и staff | телефон, адрес, email | BLOCK 4 и 5 |
| Ошибки DRF и `DEBUG` | traceback, SQL | только development; prod DEBUG запрещён модулем |
| `/health/` + `OPS_HEALTH_DETAILS` | счётчики платежей и 1С | BLOCK 7 |
| `/api/docs/` если флаг включили на сервере | полная схема | BLOCK 7, живой хост НЕ ПРОВЕРЕНО |
| Логи `register_response` / `last_status_response` | платёжные JSON | BLOCK 10 |
| `onec_payload_snapshot`, `onec_last_error` | данные заказа и текст ошибки 1С | BLOCK 9 |
| Исходники frontend `NEXT_PUBLIC_*` | URL API, флаги функций, реквизиты; секреты туда класть нельзя | BLOCK 3 |
| Source maps `.next` | логика клиента в артефакте сборки на машине разработчика | не публиковать; BLOCK 3 |
| Пример nginx и compose | имена сервисов, дефолтные порты | не секрет, но облегчает разведку |
| Django Admin на предсказуемом `/admin/` | форма входа | путь должен быть неочевидным только как дополнение, не как защита |

## 11. Сеть и хост — НЕ ПРОВЕРЕНО

Без доступа к VPS нельзя утверждать:

- какие порты слушаются снаружи;
- установлен ли nginx из примера или другой прокси;
- есть ли HSTS на прокси, rate limit, ограничение размера;
- закрыты ли 22/5432/6379/8000/3000;
- совпадает ли `REMOTE_ADDR` у Django с IP ЮKassa или с IP прокси;
- выпущен ли сертификат на `test.ringoo15.store`.

Локальные файлы говорят только, каким должен быть безопасный профиль Compose, если его действительно применили.

## 12. Сводка приоритетов для следующих блоков

Сначала проверять то, что уже анонимно и меняет деньги или чужие данные:

1. Объектный доступ к заказам, оплате, адресам, пользователям.
2. Доверие к цене, количеству и статусу оплаты из запроса клиента.
3. Webhook без allowlist и с re-fetch.
4. Admin API: группа, MFA, mass assignment роли.
5. XSS и место хранения JWT.
6. Apply 1С и загрузки файлов.
7. Скачивание бэкапа и содержимое логов.
8. Слабая изоляция dev Compose — не смешивать с оценкой production, но учитывать, если dev доступен из сети.
