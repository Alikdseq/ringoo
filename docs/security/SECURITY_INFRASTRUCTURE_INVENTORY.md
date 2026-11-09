# Инвентаризация инфраструктуры

Дата: 2026-11-07. Источник — файлы репозитория. Запущенные контейнеры и VPS не осматривались.

## Схема, как она записана в Compose

Локальный файл `docker-compose.yml` (не production):

`браузер → опубликованные 3000 и 8000 → frontend и web → db и redis в сети ringoo_network → celery и celery-beat`

Порты базы и Redis в этом файле тоже опубликованы на хост.

Задуманный production, только если поднят `docker-compose.yml` вместе с `docker-compose.prod.yml`:

`Internet → Nginx или Caddy на хосте (файлы-примеры, не сняты с VPS) → 127.0.0.1:3000 frontend и при необходимости 127.0.0.1:8000 web → db и redis без публикации портов → celery и celery-beat`

Живой путь на сервере этим файлам не равен. Это NOT TESTED.

## Сервисы

| Сервис | Образ / сборка | Порты в базовом файле | Порты в prod overlay | Сеть | Том | Healthcheck | Restart | Пользователь в образе | Лимиты |
|---|---|---|---|---|---|---|---|---|---|
| db | `postgres:15-alpine` | `${DB_PORT:-5436}:5432` | `ports: !reset []` | ringoo_network | postgres_data | `pg_isready` | только в prod: unless-stopped | в compose не задан | нет |
| redis | `redis:7-alpine` | `${REDIS_PORT:-6380}:6379` | сброшены | ringoo_network | redis_data, AOF | `redis-cli ping` | только prod | в compose не задан | нет |
| web | dev: `Dockerfile.dev`; prod: `Dockerfile` | `8000:8000` на всех интерфейсах | `127.0.0.1:8000` по умолчанию | та же | dev: код с хоста, static, media. prod: static, media, logs | HTTP `/health/` | только prod | prod: `django`. dev: root, `USER` нет | prod: 2 CPU, 1536M через `deploy.resources` |
| frontend | dev: `Dockerfile.dev`; prod: `Dockerfile` standalone | `3000:3000` | `127.0.0.1:3000` | та же | dev: код с хоста. prod: томов нет | HTTP `/` | только prod | prod: `nextjs`. dev: root | prod: 1.5 CPU, 1024M |
| celery | тот же образ, что web | нет | нет | та же | dev: код. prod: media и logs | нет | только prod | как у web | prod: 1 CPU, 1024M |
| celery-beat | тот же | нет | нет | та же | logs в prod | нет | только prod | как у web | prod: 0.5 CPU, 512M |

`privileged`, `cap_add`, `cap_drop`, `network_mode: host`, `pid: host`, сокет `/var/run/docker.sock` в compose-файлах не заданы.

`deploy.resources` лежит в prod overlay. Применяет ли его установленный на сервере Compose, не проверялось.

Отдельного контейнера Flower нет.

## Прочие файлы

- `docker-compose.ngrok.yml` — демо, не закрывает порты базы.
- `docker-compose.no-host-db-redis-ports.yml` — пишет `ports: []`. Prod-файл предупреждает, что пустой список порты не сбрасывает (RINGOO-INF-002).
- `.dockerignore` backend исключает `.env`, `.env.*`, `.git`, sqlite, media. Frontend исключает `.env`, `.next`, `node_modules`.
- `.gitignore` игнорирует `.env`, `.env.production`, `*.env`, каталог `/backups/`. Значения секретов из этих файлов в отчёт не снимались. Факт, что на диске разработчика нет локального `.env`, не проверялся обходом каталога с печатью содержимого.

## Секреты в конфигурации, без значений

| Имя | Откуда | Небезопасный fallback |
|---|---|---|
| `SECRET_KEY` | env. Production settings отвергает короткий и `django-insecure` | в `base.py` есть dev-fallback. Production его не принимает |
| JWT | тот же `SECRET_KEY`, HS256, access 30 минут, refresh 7 дней | нет отдельного ключа |
| `DB_PASSWORD` | env. В базовом compose fallback `postgres` | да, только базовый файл |
| `REDIS_PASSWORD` | env. В базовом файле может быть пустым | prod settings требуют пароль ≥ 16 или URL с паролем |
| ЮKassa, 1С, SMTP, S3 backup | env, по умолчанию интеграции выключены | пустые строки, не зашитые боевые ключи в compose |
| `BACKUP_ENCRYPTION_KEY` | env, комментарий «не коммитить» | флаг шифрования сам по себе выключен |

Боевые значения не читались и не печатались.
