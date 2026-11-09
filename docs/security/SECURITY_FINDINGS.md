# Реестр находок безопасности Ringoo

- Дата: 2026-11-07
- Статус реестра: блоки 1–8 закрыты по своим границам. Блок 8 исправил INV-001, INV-002 и PAY-001 в коде и проверил их на SQLite с mock. Реальные ЮKassa, 1С, PostgreSQL и VPS не вызывались. Это не итог по всему магазину и не допуск к запуску.
- Секреты и персональные данные в карточки не включаются.
- Браузер магазина и `test.ringoo15.store` не открывались. Динамика FE-001 и FE-002 сделана изолированно: разбор URL в Node и HTML-парсер jsdom, без записи в каталог и без учётных записей.

Шкала: CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL.

---

## RINGOO-FE-001. Открытый редирект после входа, регистрации и входа сотрудника

| Поле | Значение |
|---|---|
| ID | RINGOO-FE-001 |
| Критичность | MEDIUM (не повышалась) |
| Статус | подтверждена. Разбор URL выполнен. Клик в браузере магазина не выполнялся |
| CWE | CWE-601 |
| OWASP | Непроверенные переходы (ASVS V5) |
| CVSS 4.0 | 4.8 (AV:N/AC:L/AT:N/PR:N/UI:A/VC:N/VI:L/VA:N/SC:N/SI:N/SA:N), ориентир |
| Файлы | `frontend/src/app/login/page.tsx` 19, 47; `register/page.tsx` 20, 79; `admin/login/page.tsx` 23, 45 |

Что принимает код. Строка `next` из query без проверки уходит в `router.push` после успешного `login` / `register` / завершения staff-login.

Какие значения внешние. Конструктор `URL`, тот же, что использует Next.js (`new URL(href, location.href)`), на базе `http://127.0.0.1:3000/login` помечает чужим origin:

- `https://example.invalid/phish`
- `//example.invalid/phish` (protocol-relative, схема берётся у текущего сайта)
- `///example.invalid`
- `/\\example.invalid` и `\\example.invalid` (обратный слэш превращается в переход на чужой host)
- `https:example.invalid`
- `https://user@example.invalid/`

Свои пути `/profile`, `/orders/1`, `/login` остаются на `127.0.0.1`.

Схема `javascript:` до навигации отсекается самим Next.js (`isJavaScriptURLString` в `sequential-router-queue.js`). Это не обход.

Дальше Next.js 16.4.3 при другом origin ставит `isExternalUrl` и вызывает `completeHardNavigation` → `location.assign`. Файлы: `frontend/node_modules/next/dist/client/components/router-reducer/reducers/navigate-reducer.js`, `app-router.js`.

Другие переходы. Сброс пароля делает `router.push('/login')` — константа. Страницы, которые сами кладут `next`, кодируют только свой путь (`/profile`, `/orders`, `/wishlist`, `/admin/...`). Опасен потребитель параметра, а не эти ссылки. `returnUrl`, `callbackUrl` в `src` нет.

Оплата. `window.location.assign(redirectUrl)` на checkout, странице заказа и странице неуспешной оплаты берёт `confirmation_url` / `form_url` из ответа API и не сверяет host. Это не тот же дефект: посетитель не подставляет URL в query. Если API вернёт только адрес ЮKassa, браузер уйдёт туда штатно. Проверка, не может ли API вернуть чужой host, относится к блоку 8. Здесь это не подтверждённый открытый редирект.

Последствия FE-001. Только переход на другой сайт после того, как человек уже ввёл пароль на настоящем Ringoo. Cookie `ringoo_access` и `ringoo_refresh` на чужой origin не отправляются. Обхода входа, MFA и прав администратора нет. Практический риск — вторая форма «введите пароль ещё раз» на чужом сайте. Для сотрудника сценарий тот же по технике и сильнее как социальная инженерия; критичность из-за этого не становится HIGH: технический эффект не шире фишинга.

Ожидаемое поведение. Разрешать только путь с одним ведущим `/`, без `//`, `/\`, `\` и без схемы. Иначе `/profile` или `/admin/orders`.

Повторная проверка. Локально, тестовый пользователь, цель `https://example.invalid/` и `//example.invalid/`. Адресная строка остаётся на origin магазина. `/profile` по-прежнему открывается. То же для `/register` и `/admin/login`.

---

## RINGOO-FE-002. Stored XSS через JSON-LD

| Поле | Значение |
|---|---|
| ID | RINGOO-FE-002 |
| Критичность | HIGH (было MEDIUM) |
| Статус | подтверждена изолированным HTML-парсером. В работающий каталог маркер не записывался |
| CWE | CWE-79 |
| OWASP | A03:2021 Injection (XSS) |
| CVSS 4.0 | 7.6 (AV:N/AC:L/AT:N/PR:L/UI:P/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N), ориентир |
| Файлы | `frontend/src/lib/seo/json-ld.tsx` 11–19, 72–112, 115–133; страницы товара, категории, магазина, главная |

Почему критичность поднята. Прежний MEDIUM описывал только факт неэкранированного `<`. После разбора последствий этого мало. Скрипт выполняется на origin магазина. CSP разрешает `'unsafe-inline'`. Cookie CSRF не HttpOnly (`frontend/src/lib/csrf.ts` читает `csrftoken`). JWT access/refresh в штатном production — HttpOnly, их из `document.cookie` не прочитать, но запросы с `credentials: 'include'` уходят уже от имени того, кто открыл страницу, включая сотрудника. Общий origin у витрины и `/admin`. Автор названия товара (группа каталога или синхронизация 1С) может таким образом действовать от сессии более широкого администратора, который просто открыл карточку. Это уже не «косметический XSS». До CRITICAL не дотягивает: аноним название не меняет, прямой кражи HttpOnly-токена нет.

Кто пишет поля. Интерфейс: `/admin/products`, `/admin/products/new`, `/admin/products/[id]`, категории, магазины. Серверная проверка группы `ringoo_catalog` / `ringoo_stores` в этом блоке не переигрывалась (блок 5). Поток 1С пишет те же поля товара без участия браузера.

Какие поля попадают в `<script>`. `product.title`, `brand`, `sku`, `meta_description`, `short_description`, имя пункта хлебных крошек, имя и описание магазина, адрес. `product.description` в JSON-LD проходит грубое вырезание тегов и только если более короткие поля пусты. Название и краткое описание так не обрабатываются.

Витринный текст карточки — другой путь. `stripDescriptionHtml` (`frontend/src/lib/format-description.ts`) снимает теги, а React кладёт результат в текстовый узел. Это не HTML-контекст. Обход этой функции не даёт XSS в теле карточки. Дыра именно в JSON-LD.

Доказательство. Временный скрипт вне репозитория, jsdom 26 из `frontend/node_modules`. Вход — `JSON.stringify({ name: "</script><script>window.__hit=1</script>" })`, как делает `JsonLd`. Результат парсера: два script, второй classic, `window.__hit === 1`. Та же строка с заменой `<` на `\u003c`: один script `application/ld+json`, флаг не выставлен. Каталог, база и браузер магазина не использовались.

Метаданные Next (`generateMetadata`) идут через API Metadata, не через `dangerouslySetInnerHTML`. Отдельного sink там нет. Новости и блог в `src/app/news/[slug]` и `blog/[slug]` — заглушки, HTML статьи не рендерится.

Что XSS может и чего не может.

- Может: читать `sessionStorage` (гостевой токен заказа), читать CSRF-cookie, вызывать API с cookie сессии жертвы, подменять экран.
- Не может само по себе: прочитать `ringoo_access` / `ringoo_refresh`, пока включён cookie-режим.
- Может, если сборка с `NEXT_PUBLIC_USE_AUTH_COOKIES=0`: прочитать JWT из `localStorage`.

Ожидаемое поведение. Одна сериализация JSON-LD с заменой `<` на `\u003c`.

Повторная проверка. Изолированная база, тестовый товар с маркером в `title`, открытие карточки, маркер остаётся внутри JSON. Товар удалить. Либо повторить jsdom-проверку после правки: второй classic script не появляется.

---

## RINGOO-FE-003. Кэш личных данных переживает выход и смену пользователя

| Поле | Значение |
|---|---|
| ID | RINGOO-FE-003 |
| Критичность | MEDIUM |
| Статус | подтверждена по коду и контракту TanStack Query 5. Два тестовых аккаунта в браузере не прогонялись |
| CWE | CWE-200 |
| OWASP | A01:2021 Broken Access Control (клиентское разграничение) |
| CVSS 4.0 | 4.6 (AV:L/AC:L/AT:N/PR:N/UI:A/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N), ориентир. Вектор локальный: чужая вкладка, не удалённый злоумышленник |
| Файлы | `frontend/src/lib/providers/QueryProvider.tsx` 6–16; `frontend/src/lib/hooks/useAuth.ts` 79–84; `ProfileContent.tsx` 104–131; `checkout/page.tsx` 146–150 |

Причина. `QueryClient` один на всё приложение и живёт, пока вкладка не перезагружена. `logout` обнуляет только `['auth','me']` и удаляет `['auth','staff-access']`. Ключи `['orders']`, `['addresses']`, `['wishlist']`, `['order', id]`, `['admin', ...]` не содержат id пользователя и не сбрасываются.

Пока данные считаются свежими, повторный mount не ходит в сеть и рисует кэш. Свежесть по умолчанию 30 секунд (`staleTime: 30_000`). Адреса на checkout помечены свежими 5 минут и делят ключ `['addresses']` с профилем. Итог: второй человек, вошедший в той же вкладке, пока кэш свежий, видит заказы, адреса или избранное предыдущего.

Сервер при этом чужие записи не отдаёт. Утечка только из памяти вкладки. После полной перезагрузки кэша нет. Признак staff при выходе удаляется, поэтому чужой пользователь не остаётся «админом» в `AdminGuard` из-за старого флага. Кэш админских списков в памяти остаётся, но страница админки без нового успешного `staff-access` не рисуется.

Ожидаемое поведение. В `logout` вызывать `queryClient.clear()` (или снимать все ключи, кроме справочников каталога). В ключ личных запросов входит id пользователя.

Повторная проверка. Два синтетических пользователя, одна вкладка, без перезагрузки: пользователь A открывает профиль и checkout, выходит, сразу входит B. На экране не должно быть адресов и заказов A. Сеть для этих запросов должна уйти заново.

---

## Наблюдения блока 3, не заведённые как уязвимости

| ID | Статус | Суть |
|---|---|---|
| FE-NOTE-01 | не уязвимость | `layout.tsx`: скрипт темы — константа из исходника. Cookie `ringoo_ui_mode` читается только как `official` или `svoi`. |
| FE-NOTE-02 | задумано | Официальный клиент в production шлёт `X-Auth-Cookies: 1` и не кладёт JWT в `localStorage`. Режим `NEXT_PUBLIC_USE_AUTH_COOKIES=0` снова пишет токены в `localStorage`. Это включается явно. |
| FE-NOTE-03 | усилитель FE-002 | CSP: `script-src 'unsafe-inline' 'unsafe-eval'`. Само по себе не дыра. |
| FE-NOTE-04 | блок 8 | Платёжный `location.assign` доверяет URL из API. Allowlist host на клиенте нет. |
| FE-NOTE-05 | потенциальный риск, не подтверждён | `frontend/src/app/sitemap.ts` следует за полем `next` пагинации без сверки host. Управлять этим полем может только ответ API. Отдельной уязвимости без вредоносного API нет. |
| FE-NOTE-06 | публичные по назначению | `NEXT_PUBLIC_YANDEX_*`, `NEXT_PUBLIC_SENTRY_DSN`, реквизиты организации. Это не пароли приложения. Квоту Яндекса и проект Sentry при утечке DSN/ключа можно расходовать. Ограничение по referrer в кабинете Яндекса не проверялось. |

---

## RINGOO-API-001. Публичный API отдаёт телефон автора статьи и новости

| Поле | Значение |
|---|---|
| ID | RINGOO-API-001 |
| Критичность | HIGH |
| Статус | подтверждена на изолированной SQLite (`config.settings.test`). Рабочая база и публичный домен не использовались |
| CWE | CWE-200 |
| OWASP | A01:2021 Broken Access Control |
| CVSS 4.0 | 6.9 (AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N), ориентир. Утекает идентификатор входа, не сессия |
| Компонент | Публичный контент |
| Endpoint | `GET /api/v1/content/articles/{slug}/`, `GET /api/v1/content/news/{slug}/` |
| Файлы | `backend/apps/content/serializers.py` 48–50 и 106–108; `backend/apps/content/views.py` 49–92 и 95–137 |

Причина. `ArticleSerializer` и `NewsSerializer` доступны без авторизации и добавляют `author_phone` из `CustomUser.phone`. Телефон — `USERNAME_FIELD`, то есть логин. Список статей это поле не содержит, карточка содержит.

Доказательство. Синтетические пользователь и опубликованная статья в памяти SQLite. Анонимный `GET /api/v1/content/articles/public-post/` вернул 200 и телефон автора. Каталог и пользователи рабочей базы не читались.

Влияние. Любой клиент узнаёт логин сотрудника, который указан автором. Это облегчает подбор пароля и фишинг. Само по себе вход не открывает. Записей без автора поле не наполняет.

Рекомендация. Убрать `author_phone` из публичных сериализаторов. Если нужен контакт, это отдельное публичное поле магазина, не логин пользователя.

---

## RINGOO-API-002. Аноним читает неопубликованные статьи и новости

| Поле | Значение |
|---|---|
| ID | RINGOO-API-002 |
| Критичность | MEDIUM |
| Статус | подтверждена на той же изолированной SQLite |
| CWE | CWE-284 |
| OWASP | A01:2021 Broken Access Control |
| CVSS 4.0 | 5.3 (AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N), ориентир |
| Endpoint | `GET /api/v1/content/articles/?is_published=false`, то же для `/news/` и для карточки по slug с тем же query |
| Файлы | `backend/apps/content/views.py` 74–80 и 119–125 |

Причина. Без параметра queryset оставляет только `is_published=True`. Значение `false`, `0` или `no` переключает фильтр на черновики. ViewSet только для чтения, записью это не является. Карточка черновика дополнительно отдаёт `author_phone` и поле `content` (в модели для статьи указано, что HTML допускается).

Доказательство. Анонимный `GET /api/v1/content/articles/?is_published=false` вернул slug `draft-secret`. Карточка этого slug с тем же параметром вернула текст `INTERNAL` и телефон автора. Обычный список без параметра вернул только `public-post`.

Влияние. Черновики, включая невыпущенные тексты и логин автора, доступны без входа. На витрине Next эти страницы сейчас заглушки, API при этом отвечает.

Рекомендация. Игнорировать клиентский `is_published` на публичных view. Черновики отдавать только через `/api/v1/admin/content/` с группой `ringoo_content`.

---

## RINGOO-AUTH-001. Группа `ringoo_users` включает и выключает любой аккаунт

| Поле | Значение |
|---|---|
| ID | RINGOO-AUTH-001 |
| Критичность | MEDIUM |
| Статус | подтверждена по коду в блоке 4 и по HTTP на SQLite в блоке 5. Код не исправлялся |
| CWE | CWE-269 |
| OWASP | A01:2021 Broken Access Control |
| CVSS 4.0 | 6.0 (AV:N/AC:L/AT:N/PR:H/UI:N/VC:N/VI:L/VA:H/SC:N/SI:N/SA:N), ориентир. Нужны staff, группа и TOTP, когда OTP включён |
| Endpoint | `PATCH /api/v1/admin/users/{id}/patch/` |
| Файлы | `backend/apps/admin_api/views/users.py` 94–127 |

Причина. Сериализатор принимает `is_active`, `is_staff`, `groups`. Менять `is_staff` и `groups` может только `is_superuser`. На `is_active` такого условия нет. View требует группу `ringoo_users`, staff и, при включённом OTP, claim `admin_mfa`.

Сценарий. Сотрудник этой группы отправляет `{"is_active": false}` на суперпользователя и блокирует его вход. Либо `{"is_active": true}` на сотрудника, которого отключили, не сняв `is_staff`: доступ сотрудника возвращается без суперпользователя. Назначить себе новую группу или `is_staff` этот запрос не даёт.

Рекомендация. Запретить группе менять `is_active` у `is_superuser` и у последнего активного суперпользователя. Повторное включение staff оставить суперпользователю либо требовать отдельное подтверждение. Это не замена проверки групп.

Повторная проверка блока 5, SQLite, синтетические аккаунты. `PATCH /api/v1/admin/users/{id}/patch/` от сотрудника `ringoo_users`: выключенный staff стал `is_active=True` и остался staff (200); выключенный суперпользователь стал активным и остался суперпользователем (200); другой staff стал `is_active=False` (200); попытка выставить `is_staff=True` покупателю — 400, флаг остался False. После этих четырёх изменений в `AuditLog` прибавилось 4 записи. Сотрудник каталога и покупатель на тот же URL получили 403. Покупатель, состоящий в `ringoo_users` без `is_staff`, на список пользователей получил 403. `PUT` на тот же URL — 405. Код по-прежнему это позволяет: находка не закрыта исправлением.

---

## RINGOO-API-003. При включённых возвратах любой staff читает чужой возврат

| Поле | Значение |
|---|---|
| ID | RINGOO-API-003 |
| Критичность | MEDIUM |
| Статус | подтверждена по коду. Сейчас маршрут закрыт флагом, HTTP не вызывался |
| CWE | CWE-639 |
| OWASP | A01:2021 Broken Access Control |
| CVSS 4.0 | 5.3 при включённом флаге (AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N), ориентир. Пока `RETURNS_ENABLED` ложен, запрос получает 403 до этой проверки |
| Endpoint | `GET /api/v1/returns/{id}/`, `POST /api/v1/returns/create/` |
| Файлы | `backend/apps/returns/views.py` 86–135; `backend/apps/returns/flags.py` |

Причина. После проверки флага владелец сравнивается так: отказ только если это не владелец и пользователь не `is_staff`. Группа `ringoo_orders` здесь не требуется. Любой сотрудник, включая каталог, при открытом флаге читает чужой возврат и может создать возврат по чужому `order_id`. Список возвратов фильтруется по `user` и этот обход не использует. Админские `/api/v1/admin/returns/` требуют `ringoo_orders`.

Рекомендация. На клиентских маршрутах убрать ветку `is_staff`. Чужие возвраты оставить на admin API. Сделать это до включения `RETURNS_ENABLED`.

---

## RINGOO-AUTH-002. Refresh после блокировки выдаёт новый access, который сам не входит

| Поле | Значение |
|---|---|
| ID | RINGOO-AUTH-002 |
| Критичность | INFO |
| Статус | подтверждена на SQLite. Доступа к данным этот refresh не даёт |
| CWE | CWE-613 |
| OWASP | A07:2021 Identification and Authentication Failures |
| Endpoint | `POST /api/v1/auth/token/refresh/` |
| Файлы | `backend/apps/users/views.py` 72–92. Сериализатор не загружает пользователя |

До блокировки `GET /api/v1/auth/me/` с access — 200. После `is_active=False` тот же access на `/auth/me/`, `/orders/` и `/admin/orders/` — 401 `user_inactive`. Пароль — 401. `POST /auth/token/refresh/` со старым refresh — 200 и новое поле `access`. Этот новый access на `/auth/me/` — снова 401. Блокировка не пишет refresh в blacklist. Ротация при успешном refresh помечает предъявленный refresh, это обычная ротация.

Рекомендация. В `AdminMfaAwareTokenRefreshSerializer` находить пользователя и отвечать 401, если он неактивен, не выпуская новую пару.

---

## RINGOO-AUTH-003. Любая группа `ringoo_*` читает сводку выручки

| Поле | Значение |
|---|---|
| ID | RINGOO-AUTH-003 |
| Критичность | LOW |
| Статус | HTTP 200 на SQLite для каталога, заказов, пользователей, контента, CRM, магазинов, отчётов и `ringoo_bonus` |
| CWE | CWE-285 |
| OWASP | A01:2021 Broken Access Control |
| Endpoint | `GET /api/v1/admin/dashboard/stats/` |
| Файлы | `backend/apps/admin_api/views/dashboard.py` 15–80; `backend/apps/admin_api/permissions.py` 77–96 |

Причина. Дашборд требует любую группу `ringoo_*` или суперпользователя, не группу отчётов. Ответ содержит число заказов, выручку, средний чек и топ SKU. Телефонов и адресов там нет. Сотрудник без группы получил 403. Список заказов при этом у каталога остаётся 403.

Рекомендация. Отдавать эту сводку только `ringoo_reports` и суперпользователю, либо убрать из неё суммы для остальных групп.

---

## RINGOO-INF-001. Файл локального Compose публикует PostgreSQL и Redis

| Поле | Значение |
|---|---|
| ID | RINGOO-INF-001 |
| Критичность | HIGH как риск конфигурации. На VPS не проверялось |
| Статус | CONFIGURATION RISK. Файл прочитан. Порт снаружи не открывался |
| CWE | CWE-668 |
| Компонент | `docker-compose.yml` |
| Файл | `docker-compose.yml` 45–46 и 73–74, пароль по умолчанию строка 42 |

База публикует `${DB_PORT:-5436}:5432`, Redis `${REDIS_PORT:-6380}:6379`. Пароль Postgres по умолчанию в файле — слабый. Пароль Redis пустой, если переменная не задана, и тогда `requirepass` не включается. Backend и frontend слушают `8000` и `3000` без привязки к `127.0.0.1`. В шапке файла написано, что это не production.

`docker-compose.prod.yml` сбрасывает порты базы и Redis (`ports: !reset []`) и публикует приложение на `127.0.0.1`. Это закрывает риск только если на сервере действительно поднят overlay. Какой файл запущен на VPS, не смотрелся.

Рекомендация. На любом хосте с белым IP использовать только prod overlay. Не считать `expose` защитой. Повтор: на сервере `ss -lntp` и `docker compose ps` после разрешения, без публикации 5432/6379.

---

## RINGOO-INF-002. Overlay «без портов БД» порты не сбрасывает

| Поле | Значение |
|---|---|
| ID | RINGOO-INF-002 |
| Критичность | MEDIUM |
| Статус | CONFIGURATION RISK |
| Файл | `docker-compose.no-host-db-redis-ports.yml` 6–9; комментарий в `docker-compose.prod.yml` 58 |

`ports: []` при слиянии Compose дописывается к уже заданным портам, а не заменяет их. Prod-файл прямо говорит: нужен `ports: !reset []`. Этот вспомогательный файл reset не использует. Кто запустит его вместо prod overlay, оставит публикацию из базового файла.

Рекомендация. Заменить на `ports: !reset []`, как в prod overlay. Проверка: `docker compose -f docker-compose.yml -f docker-compose.no-host-db-redis-ports.yml config` и убедиться, что у db/redis нет `ports`. Команду в этом блоке не запускали.

---

## RINGOO-INF-003. Пример Nginx не задаёт редирект, HSTS и запрет служебных файлов

| Поле | Значение |
|---|---|
| ID | RINGOO-INF-003 |
| Критичность | MEDIUM для примера. Живой Nginx — NOT TESTED |
| Статус | CONFIGURATION RISK файла-примера |
| Файл | `docs/ops/nginx.production.example.conf` целиком (51 строка) |

В примере есть `listen 443`, заголовки nosniff, DENY и Referrer-Policy, `client_max_body_size 20m`, `Host` и жёсткий `X-Forwarded-Proto https`. Нет блока `listen 80` с редиректом, нет HSTS, нет `ssl_protocols`, нет `location` для `.env`, `.git` и каталогов backup. `X-Forwarded-For` берётся через `$proxy_add_x_forwarded_for`, то есть к цепочке клиента добавляется ещё адрес. CSP в этом файле нет. CSP витрины с `unsafe-inline` остаётся находкой FE-002 и этим файлом не лечится.

Рядом лежит `docs/ops/caddy.ringoo15.store.caddyfile`. Это тоже текст в репозитории, не снятая с VPS конфигурация. Он проксирует всё на `127.0.0.1:3000` и не показывает Django Admin наружу, если backend не публикуют отдельно.

Рекомендация. Не принимать пример за конфиг сервера. После разрешения снять `/etc/nginx` или `caddy adapt` и сравнить.

---

## RINGOO-INF-004. Штатный backup может остаться незашифрованным, restore умеет стереть схему

| Поле | Значение |
|---|---|
| ID | RINGOO-INF-004 |
| Критичность | MEDIUM |
| Статус | CONFIGURATION RISK. Скрипты не запускались, архивы не создавались |
| Файлы | `scripts/backup-set.sh` 109–124 и 134–136; `scripts/backup-db.sh` 18–21; `scripts/restore-db.sh` 31–44 |

`backup-set.sh` пишет gzip дампа и media, считает SHA256 и проверяет `gzip -t`. Шифрование age включается только если задан `AGE_RECIPIENT`. Иначе в манифесте `encrypted=0` и файлы остаются открытыми. Скрипт сам в S3 не ходит. Ротация `find -mtime +KEEP_DAYS` удаляет старые каталоги `set_*` (по умолчанию 14 дней) без проверки, что свежая копия уже лежит вне диска.

`backup-db.sh` всегда пишет открытый `.sql.gz`.

`restore-db.sh` с `--drop` удаляет все таблицы `public` и не спрашивает имя окружения. Защиты «это production» в скрипте нет.

Код выгрузки в S3 (`apps/backups/s3.py`) ставит `ACL=private` и сверяет размер. Флаг `BACKUP_OFFSITE_ENABLED` по умолчанию выключен. Подключён ли бакет, по репозиторию не видно.

Рекомендация. Не вызывать `restore-db.sh --drop` на рабочей базе. Перед эксплуатацией требовать `AGE_RECIPIENT`, отдельный drill на пустой базе и подтверждение, что cron `backup-set` вообще стоит. В этом блоке drill не делался.

---

## RINGOO-INF-005. Образы для локального Compose не задают USER

| Поле | Значение |
|---|---|
| ID | RINGOO-INF-005 |
| Критичность | LOW для локальной сборки. Production Dockerfile пользователя задаёт |
| Статус | CONFIGURATION RISK dev-образов. Работающие контейнеры не осматривались |
| Файлы | `backend/Dockerfile.dev` — директивы `USER` нет; `frontend/Dockerfile.dev` — тоже. `backend/Dockerfile` строка 69 `USER django`. `frontend/Dockerfile` строка 50 `USER nextjs` |

Prod overlay собирает web, celery и beat из `backend/Dockerfile`, то есть не от root, если запущен именно он. Базовый `docker-compose.yml` собирает `Dockerfile.dev`. Официальные образы `postgres:15-alpine` и `redis:7-alpine` в compose пользователя не переопределяют. `privileged`, `cap_add`, сокет Docker и `network_mode: host` в compose-файлах не найдены.

Рекомендация. На VPS не использовать dev-образы. Проверка после разрешения: `docker exec <web> id`.

---

## RINGOO-INV-001. Отрицательные цена и количество из XML 1С доходят до каталога

| Поле | Значение |
|---|---|
| ID | RINGOO-INV-001 |
| Критичность | MEDIUM |
| Статус | CONFIRMED на SQLite в блоке 7. Блок 8: FIXED — CODE и VERIFIED — ISOLATED TEST. NOT TESTED — LIVE INTEGRATION |
| CWE | CWE-20 |
| Файлы | `backend/integrations/onec/importer.py` 120–128 и 705–727; `backend/apps/stores/stock_ops.py` 329–336 |

`_quantity_status` считает любое ненулевое число, включая отрицательное, статусом `positive` и ставит строке действие `upsert`. `apply_catalog_import` пишет `prices[0]` в `Product.price` без проверки знака. Остаток проходит через `max(0, qty)`, поэтому `-3` становится нулём этой складской строки. `reserved_quantity` при этом поле не перезаписывает.

Доказательство. `DJANGO_SETTINGS_MODULE=config.settings.test`, движок `django.db.backends.sqlite3`, имя `file:memorydb_default?mode=memory&cache=shared`. Dry-run того же XML число товаров не изменил (`before=1 after=1`). После `apply_catalog_import` карточка `onec_code=N1` получила `price=-10.00`, строка `Stock.quantity=0`. Другие товары этот XML не удалял. XXE с `SYSTEM file:///c:/windows/win.ini` парсер отклонил: `EntitiesForbidden`.

Условие. Нужен apply: `ONE_C_API_ENABLED` и `confirm=true` у группы `ringoo_catalog`, либо прямой вызов `apply_catalog_import`. Покупатель этот XML не присылает. `ONE_C_API_ENABLED` в тестовых настройках выключен.

Последствия. Испорченная выгрузка затирает цену одной карточки отрицательным числом и обнуляет остаток склада этой позиции. Резерв поверх нового нуля код не снимает.

Исправление. В плане отклонять цену `< 0` и количество `< 0` как `skip` с записью в SyncLog, не доводя их до `upsert`. Повтор: тот же XML на пустой SQLite, цена и количество после apply не меняются.

---

## RINGOO-INV-002. Подтверждённый возврат ЮKassa не меняет заказ и не снимает резерв

| Поле | Значение |
|---|---|
| ID | RINGOO-INV-002 |
| Критичность | MEDIUM |
| Статус | CONFIRMED в блоке 7. Блок 8: FIXED — CODE и VERIFIED — ISOLATED TEST на mock. NOT TESTED — LIVE INTEGRATION. `RETURNS_ENABLED` не включался |
| Файлы | `backend/apps/payments/yookassa_service.py` 712–724; `backend/apps/orders/services/transitions.py` 27–38 |

`sync_refund_from_yookassa` при полном совпадении суммы ставит платёж в `refunded` и пишет `yookassa_refund_id`. `Order.status` функция не трогает. Вызова `release_at_store` в этом пути нет. Повтор того же `refund_id` остаётся идемпотентным. Частичная сумма после уже полного возврата статус `refunded` не заменяет второй раз: остаётся прежний `refund_id` и сообщение о повторном идентификаторе.

Доказательство. Тот же процесс SQLite. После `sync_refund_from_yookassa("rf-1")` платёж `refunded`, заказ остался `confirmed`. Второй вызов с тем же id статус не удвоил. Заказа со статусом `refunded` в FSM нет: `new → completed` и переход в `paid` отклоняются `OrderTransitionError`.

Условие. Уведомление `refund.succeeded`, которое GET `/refunds/{id}` подтверждает целиком, либо ручной возврат. `RETURNS_ENABLED` в тестовых настройках равен false, этот прогон флаг не включал.

Последствия. Деньги отмечены возвращёнными, заказ по-прежнему подтверждён, резерв, взятый при оформлении, остаётся. Новая оплата того же заказа закрыта статусом платежа `refunded` (`payment_blocked`).

Исправление. После подтверждённого полного возврата переводить заказ в согласованный конечный статус и снимать резерв тем же ключом идемпотентности, что и отмена. Повтор: SQLite, после refund `reserved_quantity` возвращается к значению до заказа.

---

## RINGOO-PAY-001. Webhook ЮKassa без подписи и без списка IP

| Поле | Значение |
|---|---|
| ID | RINGOO-PAY-001 |
| Критичность | LOW |
| Статус | Блок 7: CONFIGURATION RISK, подделка оплаты не прошла. Блок 8: FIXED — CODE и VERIFIED — ISOLATED TEST. Боевой список IP не задан. NOT TESTED — LIVE INTEGRATION |
| Файлы | `backend/apps/payments/views.py` 285–293; `backend/config/settings/base.py` 361–366 |

`YooKassaWebhookView` — `AllowAny`, без заголовка подписи. `YOOKASSA_WEBHOOK_IP_ALLOWLIST` пуст, если переменная окружения пустая: код прямо пишет, что тогда доверие только к повторному GET. Тело webhook само по себе в `paid` не переводит. `sync_payment_from_yookassa` сверяет сумму, валюту `RUB`, `metadata.order_id`, `metadata.payment_id` и id платежа. Несовпадение даёт `needs_review`, не `paid`.

Доказательство. SQLite, клиент ЮKassa заменён заглушкой, сеть не открывалась. Тело `succeeded` при GET `pending` оставило платёж `pending` и заказ `new`. Сумма `1.00` и валюта `USD` дали `needs_review`, заказ `new`. Совпадающий GET перевёл платёж в `paid` и заказ `new → confirmed` один раз; повтор webhook второй `paid` не создал. Неизвестный id вернул `None`. Оплата после отмены при политике `manual` оставила заказ `cancelled` и платёж `needs_review`.

Исправление. На сервере заполнить allowlist адресами ЮKassa. Это не замена сверки GET. Повтор после разрешения: запрос не с адреса из списка получает 403 и GET не вызывает.

---

## Наблюдения блока 4, не заведённые как уязвимости

| ID | Статус | Суть |
|---|---|---|
| BE-NOTE-01 | защитный механизм подтверждён | Цена, `total_amount`, `delivery_cost` и `bonus_used` в `OrderCreateSerializer.validate` перезаписываются с каталога. Клиентское число не становится суммой заказа. |
| BE-NOTE-02 | защитный механизм подтверждён | `PATCH /api/v1/auth/me/` пишет только `marketing_opt_in`. На SQLite тело с `is_staff: true` оставило `is_staff=False`. |
| BE-NOTE-03 | защитный механизм подтверждён | `GET /api/v1/orders/{id}/` другого пользователя вернул 404. Список заказов пользователя A был пуст. `GET /api/v1/admin/orders/` без staff вернул 403. |
| BE-NOTE-04 | задумано, не полный заказ | `GET /api/v1/orders/track/` и `/status/` по номеру и телефону отдают статус, тип оплаты и доставки, без адреса и позиций. Полный заказ — только владелец или guest token. Лимит `order_track` 5/minute. Динамически не гонялся. |
| BE-NOTE-05 | остаточный риск, не новая дыра | Logout вносит refresh в blacklist. Access JWT до истечения (30 минут в настройках) остаётся пригодным. Так устроен SimpleJWT без отзыва access. |
| BE-NOTE-06 | не подтверждено как SSRF | Исходящие URL 1С, ЮKassa, Сбера и геокодера собираются из настроек и фиксированного host Яндекса. Клиентский URL в запрос не подставляется. У 1С нет запрета частных IP, если базовый URL сам на них указывает. Это настройка, не ввод покупателя. |
| BE-NOTE-07 | закрыто блоком 5 по Django Admin и TOTP | Смена статуса заказа группой заказов и скачивание бэкапа по-прежнему не выполнялись: первое меняет заказ, второе отдаёт дамп. GET бэкапа без архива для чужой группы — 403. |
| BE-NOTE-08 | не уязвимость | Access после `is_active=False` отклоняется на каждом запросе (`user_inactive`). Это не отзыв через blacklist, а проверка пользователя в `JWTAuthentication.get_user`. |
| BE-NOTE-09 | не уязвимость | Django Admin не смотрит группы `ringoo_*`. Сотрудник каталога после входа, в том числе с верным TOTP, получает 403 на списки заказов, пользователей и платежей. Суперпользователь эти списки открывает. Модельных прав Django у нового staff нет. |
| BE-NOTE-10 | recovery-кодов TOTP нет | `django_otp.plugins.otp_static` не подключён. API отключения TOTP нет. |
