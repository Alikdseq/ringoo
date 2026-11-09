# Матрица проверок безопасности

Документ покрывает фронтенд (блок 3) и backend API (блок 4). Оплата, 1С, Django Admin и инфраструктура остаются в своих блоках. PASS не ставится там, где нужен браузер магазина или боевой сервер, а их не было.

Дата: 2026-11-07.

| Компонент | Проверки | Результат | Критичность | Статус |
|---|---|---|---|---|
| Вход `/login` | `next` → `router.push` | Чужой origin, `//host`, `///host`, обратный слэш уводят с сайта после успешного пароля. `javascript:` режет Next.js | MEDIUM | FAIL |
| Регистрация `/register` | тот же `next` | Тот же приёмник, без проверки пути | MEDIUM | FAIL |
| Вход сотрудника `/admin/login` | тот же `next` | Тот же приёмник. Технически фишинг, не обход MFA | MEDIUM | FAIL |
| Сброс пароля | `router.push` после успеха | Жёстко `/login` | — | PASS (код) |
| Забыли пароль | редирект после отправки | Перехода по параметру нет | — | PASS (код) |
| Ссылки «войти» с витрины | формирование `next` | В параметр кладётся свой путь (`pathname`, `/profile`, `/orders`, `/wishlist`, `/admin`) | — | PASS (код) |
| Оплата: checkout, заказ, fail | `location.assign(form_url)` | Клиент не сверяет host. Подмена из query не найдена. Доверие к API — блок 8 | — | PARTIAL |
| JSON-LD товара, категории, магазина | `dangerouslySetInnerHTML` + `JSON.stringify` | `<` не экранируется. jsdom: второй script выполняется. `\u003c` убирает выполнение | HIGH | FAIL |
| Текст описания товара | `stripDescriptionHtml` + текстовый узел React | Теги снимаются, в HTML-узел не вставляются | — | PASS (код) |
| Скрипт темы в `layout.tsx` | константа, не ввод пользователя | Пользовательской строки в скрипте нет | — | PASS (код) |
| Новость и блог `[slug]` | HTML контента | Заглушки, тело статьи из API не рендерится | — | NOT APPLICABLE |
| Metadata Next | `generateMetadata` | Не через `dangerouslySetInnerHTML` | — | PASS (код) |
| CSP | `next.config.ts` | `'unsafe-inline'` и `'unsafe-eval'` не сдерживают FE-002 | LOW как самостоятельный пробел | PARTIAL |
| `NEXT_PUBLIC_*` | все чтения в `frontend` | Секретов оплаты, Django и 1С в клиентских переменных нет. Публичны URL, флаги, имена cookie, ключ карт, DSN, реквизиты | — | PASS (код) |
| Source maps | конфиг, `.next/static`, Dockerfile | `productionBrowserSourceMaps` нет. В `.next/static` карт 0. Sentry sourcemaps отключены. Серверные `.map` лежат в локальном `.next/server` (452) и браузеру Next их не отдаёт | INFORMATIONAL для карт на диске сборки | PASS (публикация) |
| React Query | ключи, `logout`, `staleTime` | Личные ключи без id пользователя. Выход не чистит заказы и адреса. Checkout держит адреса свежими 5 минут | MEDIUM | FAIL |
| Признак staff в кэше | `removeQueries` при logout | Ключ staff-access при выходе удаляется | — | PASS (код) |
| Хранение JWT | cookie-режим и `localStorage` | Production по умолчанию не пишет access/refresh в `localStorage`. Явный `=0` пишет | — | PASS (код) при cookie-режиме |
| Гостевой токен заказа | `sessionStorage` | Доступен скрипту страницы. Имеет значение вместе с FE-002 | LOW сам по себе | PARTIAL |
| CSRF-заголовок | `client.ts`, cookie `csrftoken` | На небезопасных методах в cookie-режиме заголовок ставится. Cookie не HttpOnly, поэтому XSS её читает | — | PASS для чужого сайта; слабо при XSS |
| Server Actions | поиск `'use server'` | В `src` нет | — | NOT APPLICABLE |
| Route Handlers | `src/app/**/route.ts` | Нет. Прокси — `src/proxy.ts` на фиксированный `RINGOO_API_PROXY_TARGET` | — | PASS (код) |
| SSRF sitemap | `data.next` | Host не сверяется. Эксплуатация требует вредоносного JSON API | — | PARTIAL |
| Серверные fetch каталога | `getApiV1BaseUrl()` | URL из env, не из query браузера | — | PASS (код) |
| `console.*` | `src` | Один `console.warn` в development про режим cookie. Токенов нет | — | PASS (код) |
| Ошибки UI | `getFriendlyErrorMessage` | 500 не показывает тело. Страница входа показывает `detail` ответа как есть | — | PARTIAL |
| Изображения | `next/image` `remotePatterns` | Любой `https` host с путём `/media/**`. В контексте `<img>` скрипт SVG не выполняется | LOW | PARTIAL |
| Django Admin `/admin/` | аноним, покупатель, staff каталога, суперпользователь, TOTP | Аноним и покупатель 302 на вход. Каталог: индекс 200 без списка заказов, changelist заказов, пользователей, платежей и POST action — 403. Суперпользователь: эти changelist 200. С OTP: пароль без кода остаётся на форме, верный код пускает, повтор кода не пускает | — | PASS для изоляции моделей. OTP проверен на SQLite |
| TOTP admin API | пароль без claim, код, повтор | Без claim при включённом OTP каталог получает 403. Верный код выдаёт access и открывает товары, заказы остаются 403. Повтор того же кода — 400. Неверный код — 400. Без устройства — 403. Покупатель — 403 | — | PASS |
| Access после `is_active=False` | `/auth/me/`, заказы, admin, refresh | Старый и новый access — 401. Refresh endpoint — 200 | INFO | FAIL только как отсутствие отзыва refresh. Данные не открываются |
| Группы `ringoo_*` | GET admin-контуров | Чужая группа 403, своя 200. Дашборд 200 у любой группы | LOW | FAIL на дашборде, PASS на списках |
| `ringoo_users` и `is_active` | PATCH синтетических пользователей | Включает staff и суперпользователя, выключает другого staff. `is_staff` не ставит. Аудит пишется | MEDIUM | FAIL |
| Публичные статьи и новости | `author_phone`, фильтр `is_published` | Аноним получил телефон автора и черновик на SQLite | HIGH / MEDIUM | FAIL |
| Заказ покупателя | queryset, цена, статус | Чужой заказ 404, список пуст. Цена в `validate` затирается. POST создания на SQLite не вызывался | — | PASS для IDOR карточки. PARTIAL для гонки остатка |
| Профиль `/auth/me/` | mass assignment | `is_staff` в PATCH не записался | — | PASS (SQLite) |
| Admin API `/api/v1/admin/orders/` | staff | Покупатель получил 403 | — | PASS для анонима и покупателя. Матрица групп не гонялась |
| Оплата `/orders/{id}/pay/` | владелец, сумма | Шлюз в коде. ЮKassa не вызывалась | — | PARTIAL |
| Host | `ALLOWED_HOSTS` | `evil.example` → 400. VPS не смотрелся | — | PARTIAL |
| SSRF | клиенты 1С, ЮKassa, Яндекс | URL покупателя в запрос не входит | — | PASS (код) |
| Возвраты | флаг и `is_staff` | При включении флага любой staff читает чужой возврат. Сейчас флаг закрывает маршрут | MEDIUM | FAIL по коду, не достижимо при флаге по умолчанию |
| Пользователи admin | `is_active` | Группа `ringoo_users` не ограничена на суперпользователе | MEDIUM | FAIL (код) |
| Logout | blacklist | Refresh отзывается, access до exp нет | — | PARTIAL |
| Compose базовый | порты db/redis, пароли | 5436 и 6380 опубликованы, пароль базы по умолчанию слабый, Redis без пароля если env пуст | HIGH как конфигурация | FAIL для файла. VPS NOT TESTED |
| Compose prod overlay | порты, пользователь, restart | Порты db/redis сброшены, 3000/8000 на 127.0.0.1, `USER` в prod Dockerfile, unless-stopped | — | PASS по файлу. Сервер NOT TESTED |
| Overlay no-host ports | `ports: []` | Не сбрасывает порты базового файла | MEDIUM | FAIL |
| Пример Nginx | редирект, HSTS, dotfiles | Примера недостаточно. Живой конфиг не снимался | MEDIUM для примера | NOT TESTED на VPS |
| TLS домена | сертификат | Запросов к домену не было | — | NOT TESTED |
| Django production settings | DEBUG, HSTS, OTP, Redis, роль БД | Модуль не стартует при слабых значениях | — | PASS по коду модуля |
| Celery / beat | пользователь, порты, расписание | В prod без порта наружу. Healthcheck нет. Задачи не запускались | — | PARTIAL |
| backup-set / restore | шифрование, drill | Без AGE дамп открытый. `--drop` без предохранителя. Drill не было | MEDIUM | FAIL по скрипту. Факт копий NOT TESTED |
| S3 backup | флаг и ACL | Код private ACL. Флаг по умолчанию выкл. Бакет не вызывался | — | NOT TESTED |
| Оплата ЮKassa | сумма, чужой заказ, повтор | Сумма из `Order.total_amount`. Чужой заказ 403. Повтор открытого платежа переиспользуется. Уже `paid` — `already_paid`. Отменённый — `order_cancelled` | — | NOT VULNERABLE на SQLite с mock. Живой шлюз NOT TESTED |
| XML 1С | XXE, dry-run, apply | Отрицательные и нечисловые цена и остаток не перезаписывают карточку. Dry-run не пишет. Явный ноль по-прежнему пишется | — | VERIFIED — ISOLATED TEST. Живая 1С NOT TESTED |
| Склад, последняя единица | `reserve_atomic` | Второй последовательный резерв на SQLite не проходит. Полный возврат незабранного заказа снимает резерв один раз и не увеличивает quantity | — | PARTIAL. Гонка PostgreSQL NOT TESTED |
| Webhook ЮKassa | подпись, сумма, повтор | Тело `succeeded` без совпадающего GET не оплачивает. Пустой allowlist не считается фильтром. Непустой список сверяет `REMOTE_ADDR` | — | VERIFIED — ISOLATED TEST. Боевые IP не заданы |
| Возврат ЮKassa | идемпотентность, склад | Полный возврат: платёж `refunded`, заказ `new`/`confirmed` → `cancelled`, резерв один раз. Частичный не двигает склад. Выданный заказ не пополняется | — | VERIFIED — ISOLATED TEST. Провайдер не вызывался |
| FSM заказа | переходы | `new → completed` и статус `paid` отклонены. Оплата ставит `confirmed`, не отдельный статус оплаты | — | PASS по таблице и SQLite |
