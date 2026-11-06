# FINAL Deployment Checklist — PUBLIC DEMO (ringoo15.store)

Режим: **без** Sber / ЮKassa / 1С / онлайн-кассы / реальных платежей.

## Локально (репозиторий)

- [x] Prod Compose: DB/Redis без public ports; web/frontend на `127.0.0.1`
- [x] Admin MFA claim для `/api/v1/admin` + Next admin TOTP
- [x] `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED` ARG (default 0)
- [x] Backend `payments_disabled` если Sber OFF
- [x] Vitest зелёный (после финальной валидации)
- [x] `.env.production.example` под `ringoo15.store`
- [x] Caddyfile: `docs/ops/caddy.ringoo15.store.caddyfile`

## READY FOR VPS — REMAINING MANUAL ACTIONS (`ringoo15.store`)

Выполняет **владелец** на VPS. Не запускать из Cursor без разрешения.

### 0. DNS

```text
A     ringoo15.store      → <VPS_IP>
A     www.ringoo15.store  → <VPS_IP>
```

Дождаться пропагации: `dig +short ringoo15.store`

### 1. Сервер / firewall

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status
```

Не открывать 5432, 6379, 8000, 3000.

### 2. Код и env

```bash
cd /opt/ringoo   # или ваш путь к клону
cp .env.production.example .env.production
# Отредактируйте .env.production:
#   SECRET_KEY, POSTGRES_BOOTSTRAP_PASSWORD, DB_PASSWORD, REDIS_PASSWORD
#   ALLOWED_HOSTS=ringoo15.store,www.ringoo15.store,web,backend
#   CORS/CSRF/FRONTEND/PUBLIC = https://ringoo15.store (+ www)
#   NEXT_PUBLIC_* = https://ringoo15.store ...
#   SBER_ECOM_ENABLED=false, ONE_C_*=false, NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED=0
```

### 3. Проверка Compose

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production config > /tmp/ringoo-prod.resolved.yml
# Убедиться: db/redis без published; web/frontend host_ip 127.0.0.1; нет .env.development
```

### 4. Запуск

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production up -d --build
# НЕ использовать: docker compose down -v
```

### 5. БД роль + migrate (после бэкапа пустой БД)

```bash
# SQL: docs/ops/postgres_app_role.sql (от bootstrap)
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production \
  exec web python manage.py migrate --noinput
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production \
  exec web python manage.py collectstatic --noinput
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production \
  exec web python manage.py createsuperuser
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production \
  exec web python manage.py check --deploy
```

### 6. MFA enroll

См. `docs/ops/ADMIN_MFA_SETUP.md` — создать TOTP device для superuser, просканировать QR один раз.

### 7. TLS (Caddy)

```bash
# Установить Caddy, подставить docs/ops/caddy.ringoo15.store.caddyfile
# Caddy получит сертификат Let's Encrypt автоматически при верном DNS
systemctl reload caddy
curl -I https://ringoo15.store
```

### 8. Smoke

- https://ringoo15.store — главная / каталог
- Корзина → оформление (наличные / карта при получении)
- Онлайн-оплата **не** видна
- `/admin/login` — пароль + TOTP
- С внешней сети: 5432/6379/8000/3000 закрыты

### 9. Backup

`docs/ops/BACKUP_AND_RESTORE.md` + `.env.backup.example` (age + offsite) — **до** публичного трафика с ПДн.

## Запрещено сегодня

- Включать онлайн-оплату / Sber / 1С
- DEBUG=True
- Публиковать DB/Redis на 0.0.0.0
- Commit секретов
