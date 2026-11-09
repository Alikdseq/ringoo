# Разбор deployment, Nginx, TLS и Django production

Дата: 2026-11-07. VPS не открывался. Публичный домен не запрашивался.

## Что в репозитории считается production

Запуск, как его описывает `docker-compose.prod.yml`: оба файла сразу, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DEBUG=False`, OTP включён, `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`, CORS и CSRF обязательны (синтаксис `${VAR:?}`). Gunicorn, не `runserver`. Код с хоста в prod-контейнер web не монтируется.

Это описание намерения. Что сейчас крутится на сервере — NOT TESTED.

## Django production settings

Модуль `backend/config/settings/production.py` при загрузке падает, если:

- `DEBUG` истинный;
- `SECRET_KEY` короче 48 символов или похож на dev-ключ;
- пустой `ALLOWED_HOSTS` (кроме особого пути Vercel);
- выключен `ADMIN_OTP_ENABLED`;
- роль БД из набора `postgres` / `root` / `admin` или пароль короче 16 и из слабого списка;
- нет пароля Redis;
- `CORS_ALLOW_ALL_ORIGINS`;
- пустые CORS и CSRF origins.

Включённые по умолчанию флаги, если процесс вообще стартовал с этим модулем:

- `SECURE_SSL_REDIRECT` True (на Vercel False);
- `SESSION_COOKIE_SECURE` и `CSRF_COOKIE_SECURE` True;
- `SECURE_CONTENT_TYPE_NOSNIFF` True;
- `SECURE_HSTS_SECONDS` 31536000, поддомены включены, preload по умолчанию выключен;
- `X_FRAME_OPTIONS=DENY`;
- `SECURE_PROXY_SSL_HEADER` только если `TRUST_PROXY` (в prod compose по умолчанию 1);
- `USE_X_FORWARDED_HOST` в настройках не задан, то есть Django его не включает;
- пароли: Argon2 в base;
- JWT: HS256, подпись тем же `SECRET_KEY`;
- логи: фильтр маскирует email и телефон в сообщении. Отдельного фильтра JWT и TOTP в `RedactPIIFilter` нет;
- `SESSION_COOKIE_HTTPONLY` явно не переопределяется. Значение Django по умолчанию — True. Отдельной строкой в production.py это не закреплено.

`TRUST_PROXY=1` доверяет `X-Forwarded-Proto`. Это безопасно только если до Django нельзя прийти мимо proxy. Prod compose слушает backend на localhost. Если кто-то откроет 8000 на 0.0.0.0, клиент сможет подделать протокол. Живой bind — NOT TESTED.

## Nginx и Caddy

`docs/ops/nginx.production.example.conf` — пример на `shop.example.com`. Весь `/` идёт на `127.0.0.1:3000`. Отдельный location API закомментирован. Django Admin снаружи этим примером не проксируется: публичный `/admin` попадёт в Next.js, а Django Admin останется на порту backend, если тот только на localhost.

Чего в примере нет: редирект с 80, HSTS, `ssl_protocols`, запрет `.git` и `.env`, CSP. `X-Forwarded-For` дописывается к заголовку клиента. Это RINGOO-INF-003.

`docs/ops/caddy.ringoo15.store.caddyfile` тоже лежит в git как текст «положить на VPS». Он не является снимком `/etc/caddy/Caddyfile`.

Заголовки Django (HSTS, nosniff, DENY) работают, когда запрос дошёл до Django. Если снаружи только Next.js, заголовки витрины задаёт Next, не этот пример. CSP витрины с `unsafe-inline` разобрана в блоке 3 и здесь не стала безопасной.

## TLS

Сертификаты, срок, версии протокола и редирект на живом домене — NOT TESTED. Внешний SSL-скан не делался.

Команды на потом, после разрешения, без смены конфигов:

```bash
ss -lntp
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
curl -sI http://127.0.0.1/
curl -sI https://<домен>/
# версию TLS смотреть локально на сервере, не с этой машины
```

Истечение сертификата в репозитории никак не обрабатывается, кроме подсказки certbot/Caddy в документации.

## Перезапуск

Prod overlay ставит `restart: unless-stopped` всем шести сервисам. Базовый файл политику не задаёт. После перезагрузки VPS контейнеры поднимутся сами только если демон Docker включён и стек создан с этой политикой. Это не проверялось. Данных в volume Postgres и Redis AOF файлы не стирают. Очередь Celery живёт в Redis: при пустом Redis незавершённые задачи пропадут. Beat при простое не догоняет пропущенные тики сам по себе.

Уведомления о падении в коде не шлются. Есть команда `report_ops_alerts` и текст в `docs/ops/MONITORING_AND_ALERTING.md`. Cron на VPS — NOT TESTED.
