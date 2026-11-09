# Получение релиза Ringoo на VPS через Git

Документ для **контролируемого первого развёртывания** на VPS.
Не включает включение боевой ЮKassa, рабочей 1С и коммерческий запуск витрины.

Связанные файлы:

- `docs/PRODUCTION_DEPLOY.md` — канонический compose/env
- `docs/deployment/PRE_DEPLOYMENT_READINESS_REPORT.md` — статус готовности
- `docs/ops/ROLLBACK_PROCEDURE.md`, `docs/ops/BACKUP_AND_RESTORE.md`
- `.env.production.example` — шаблон секретов (без реальных значений)

## 1. Ветка

Используйте ветку **`main`** репозитория GitHub `Alikdseq/ringoo`.

На VPS не работайте из произвольных feature-веток без явного согласования.

## 2. Первичное получение кода

На сервере (пример путей — замените на свои каталоги):

```bash
sudo mkdir -p /opt/ringoo
sudo chown "$USER":"$USER" /opt/ringoo
cd /opt/ringoo
git clone https://github.com/Alikdseq/ringoo.git .
git checkout main
git rev-parse HEAD   # зафиксируйте SHA в журнале деплоя
```

SSH-ключ или deploy token храните только на сервере; не коммитьте.

## 3. Безопасный `git pull` при обновлении

```bash
cd /opt/ringoo
git fetch origin
git status
git log --oneline HEAD..origin/main   # что придёт
# Сделайте backup БД/media ДО обновления кода при уже работающем стенде
git pull --ff-only origin main
git rev-parse HEAD
```

Правила:

- Только `--ff-only`. При расхождении остановитесь и разберите вручную.
- Не используйте `git reset --hard`, `git clean -fd`, `git push --force` на VPS.
- Не коммитьте `.env.production` на сервере в Git.

## 4. Переменные окружения (заполнить вручную)

```bash
cp .env.production.example .env.production
chmod 600 .env.production
# Отредактируйте .env.production уникальными секретами
```

Обязательно задать (имена; значения не публикуются):

| Переменная | Назначение |
|---|---|
| `SECRET_KEY` | Django ≥48 случайных символов |
| `ALLOWED_HOSTS` | Хосты API/сайта |
| `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` | HTTPS origins фронта |
| `POSTGRES_BOOTSTRAP_PASSWORD` | Пароль владельца тома Postgres |
| `DB_PASSWORD` / `DATABASE_URL` | Роль приложения `ringoo_app` |
| `REDIS_PASSWORD` / `REDIS_URL` | Redis с паролем |
| `NEXT_PUBLIC_SITE_URL` / `NEXT_PUBLIC_API_V1_URL` | Публичные URL (build-time) |
| `DJANGO_ADMIN_URL` | Нестандартный путь Django Admin |
| `ADMIN_OTP_ENABLED=1` | Обязателен в production |

Первый запуск — интеграции **выкл.**:

```text
YOOKASSA_ENABLED=0
NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED=0
SBER_ECOM_ENABLED=false
ONE_C_API_ENABLED=false
ONE_C_ORDER_SYNC_ENABLED=false
ONE_C_SYNC_PARTNER_ON_REGISTER=false
ONE_C_CATALOG_SYNC_ENABLED=0
RETURNS_ENABLED=0
BACKUP_OFFSITE_ENABLED=0
```

SMTP, Sentry, Telegram, S3 — по мере готовности; пустые секреты не заполняйте фиктивными «боевыми» значениями.

## 5. Файлы, которые создаются только на сервере

| Файл | В Git? |
|---|---|
| `.env.production` | Нет |
| `.env.backup` (опционально) | Нет |
| TLS certificates / private keys | Нет |
| Nginx/Caddy site config на хосте | Обычно вне репо или из `docs/ops` шаблонов |
| Локальные `media/`, `backups/`, `logs/` | Нет |

## 6. PostgreSQL

Compose поднимает Postgres из overlay. После первого `up`:

1. Создайте роль приложения least-privilege по `docs/ops/POSTGRES_LEAST_PRIVILEGE.md` / `docs/ops/postgres_*.sql`.
2. Убедитесь, что `DATABASE_URL` указывает на `ringoo_app`, а не bootstrap-суперпользователя тома.
3. Порты DB **не** публикуйте на `0.0.0.0` (prod overlay: `ports: !reset []`).

## 7. Redis

- Обязателен пароль (`REDIS_PASSWORD` + URL с `redis://:…@`).
- Порт наружу не публиковать.
- Healthcheck в prod overlay использует пароль.

## 8. Docker Compose (production)

Требуется Docker Compose **≥ 2.24**.

```bash
export RINGOO_GIT_SHA="$(git rev-parse --short HEAD)"
export RINGOO_RELEASE="$(git rev-parse --short HEAD)"

docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production config

docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production up -d --build
```

Не запускайте один `docker-compose.yml` на белом IP без prod overlay.

Миграции **не** должны применяться «молча» при каждом старте контейнера без явной политики. На первом деплое — вручную после бэкапа.

## 9. Миграции

```bash
# Backup сначала (см. docs/ops/BACKUP_AND_RESTORE.md)
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production exec web \
  python manage.py showmigrations

docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production exec web \
  python manage.py migrate --plan

docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production exec web \
  python manage.py migrate --noinput

docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production exec web \
  python manage.py collectstatic --noinput
```

На сервере **не** запускайте `makemigrations`.

Новые миграции релиза (должны быть в Git):
`payments.0004_payment_refund_line`, `products.0008_onec_catalog_synclog`.

## 10. Проверка API

```bash
curl -fsS http://127.0.0.1:8000/health/
# через reverse proxy (ringoo15.store):
curl -fsS https://ringoo15.store/health/
curl -fsS https://ringoo15.store/api/v1/  # ожидать осмысленный ответ/роутинг
```

Ожидайте `git_sha` / release в health при корректных build args.

## 11. Проверка frontend

```bash
curl -fsS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/
curl -fsS -o /dev/null -w "%{http_code}\n" https://ringoo15.store/
```

Проверьте, что витрина открывается, checkout не предлагает выключенную онлайн-оплату, админ-панель Next требует staff JWT.

## 12. Nginx / HTTPS

- Терминируйте TLS на хосте (Caddy/Nginx).
- Проксируйте только `127.0.0.1:3000` и `127.0.0.1:8000`.
- Выставьте `TRUST_PROXY=1`, корректный `AXES_IPWARE_PROXY_COUNT`.
- См. `docs/ops/VPS_FIREWALL_AND_TLS.md`.

## 13. Celery / Celery Beat

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production logs --tail=100 celery celery-beat
```

Оба сервиса должны быть `running`. Catalog sync / order sync 1С при первом старте **не** включать.

## 14. Логи

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production logs --tail=200 web frontend
```

Не сохраняйте в тикеты пароли, токены ЮKassa, тела webhook с PII.

## 15. Административная панель

1. Создайте суперпользователя один раз:
   `python manage.py createsuperuser` внутри `web`.
2. Зарегистрируйте TOTP (`docs/ops/ADMIN_MFA_SETUP.md`) — в production OTP обязателен.
3. Django Admin: путь из `DJANGO_ADMIN_URL` (не `/admin/` по умолчанию в шаблоне).
4. Staff UI Next: `/admin` на фронте — отдельный JWT+RBAC контур.

## Диагностика при сбое

| Симптом | Действие |
|---|---|
| `compose config` требует переменную | Допишите missing `${VAR:?}` в `.env.production` |
| `ImproperlyConfigured` SECRET/DB/Redis | Слабый/пустой секрет — сгенерируйте заново |
| DB connection refused | `ps`/health db; URL host=`db` |
| 502 от proxy | `ps` web/frontend; publish только localhost |
| Миграция упала | Не повторяйте вслепую; восстановите из backup |
| Нужен откат кода | `docs/ops/ROLLBACK_PROCEDURE.md` + image tag |

## Чего не делать на первом деплое

- Не включать `YOOKASSA_ENABLED=1` / live keys
- Не включать `ONE_C_*` apply/Beat
- Не слать реальные платежи и не дергать рабочую 1С
- Не публиковать 5432/6379
- Не коммитить `.env.production` и сертификаты
