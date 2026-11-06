# Production Deployment Checklist — Ringoo (отдельный VPS)

Используйте вместе с `.env.production.example` и `docker-compose.prod.yml`.

## A. Перед деплоем (локально / в репозитории)

- [ ] Есть `.env.production` (не в Git) с уникальными `SECRET_KEY`, DB/Redis паролями
- [ ] `DB_USER` ≠ `postgres` (роль `ringoo_app`, см. `docs/ops/postgres_app_role.sql.example`)
- [ ] `ADMIN_OTP_ENABLED=1`, выбран нестандартный `DJANGO_ADMIN_URL`
- [ ] `SBER_ECOM_ENABLED=false`, `ONE_C_*=false`, `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED=0`
- [ ] `NEXT_PUBLIC_ORG_INN` / `OGRN` заполнены для публичных реквизитов
- [ ] Заполнены `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` (https)

## B. VPS / сеть

- [ ] SSH только по ключам, парольный login выключен
- [ ] Firewall: публично только 80/443 (и SSH с ограничением)
- [ ] Порты 5432/6379/5436/6380 **закрыты** снаружи
- [ ] Docker API не слушает 0.0.0.0
- [ ] Диск с шифрованием (LUKS / провайдер) — рекомендуется

## C. Запуск Compose

```bash
# Docker Compose ≥ 2.24 (нужен !override в docker-compose.prod.yml)
cp .env.production.example .env.production
# отредактируйте .env.production

# Compose ≥ 2.24: в prod overlay используются !override и ports: !reset []
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production config > /tmp/ringoo-prod.resolved.yml
# Проверьте: у db/redis нет published ports; нет .env.development; нет bind ./backend

docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production up -d --build
```

- [ ] Docker Compose ≥ 2.24
- [ ] `config` не содержит published DB/Redis ports (`ports: !reset []` в overlay)
- [ ] Web/celery без `./backend:/app`
- [ ] Нет `env_file: .../.env.development`
- [ ] В контейнере web: `DB_USER`/`DATABASE_URL` — роль `ringoo_app`, не `postgres`

## D. После старта контейнеров

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web \
  python manage.py check --deploy

# Миграции — только после бэкапа пустой/новой БД
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web \
  python manage.py migrate --noinput

docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web \
  python manage.py collectstatic --noinput

docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web \
  python manage.py createsuperuser
```

- [ ] `check --deploy` без критических ошибок
- [ ] Superuser создан; в Django Admin добавлен TOTP device **до** выдачи ссылки в интернет
- [ ] Все staff учётные записи с TOTP

## E. TLS (Caddy или Nginx)

- [ ] Пример: `docs/ops/caddy.production.example.caddyfile` или `nginx.production.example.conf`
- [ ] `TRUST_PROXY=1`, `AXES_IPWARE_PROXY_COUNT=1`
- [ ] Браузер: сайт только по HTTPS, cookies Secure

## F. Backup (обязательно до публичного трафика)

Рекомендуемые RPO ≤ 24h, RTO ≤ 4h (уточните у владельца).

1. Ежедневный `pg_dump` (custom format) на VPS  
2. Шифрование (`gpg` / age) **ключом, который не хранится только на том же VPS**  
3. Копия в отдельное хранилище (S3/Backblaze/другой регион)  
4. Ежемесячный restore drill на пустую staging DB  
5. Доступ к backup — только ops; аудит доступа

Пока drill не выполнен — статус backup = **NOT VERIFIED**.

## G. Внешняя проверка перед открытием

- [ ] Скан портов с внешней сети: 5432/6379 закрыты  
- [ ] TLS grade / сертификат валиден  
- [ ] `/health/` не отдаёт stack/SQL text  
- [ ] Онлайн-оплата скрыта  
- [ ] Smoke: каталог → корзина → заказ (cash)  

## H. Запрещено до отдельного согласования

- Включение Sber / ЮKassa / 1С write / касса  
- `DEBUG=True`  
- Публикация DB/Redis  
- Commit секретов в Git  
