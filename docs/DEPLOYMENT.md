# Руководство по деплою

## Подготовка к деплою

### Требования

- Сервер с Ubuntu 20.04+ или аналогичный
- Docker и Docker Compose установлены
- Минимум 2GB RAM, 2 CPU cores
- 20GB свободного места на диске
- Доменное имя (для production)

## Production окружение

### 1. Подготовка сервера

```bash
# Обновить систему
sudo apt update && sudo apt upgrade -y

# Установить Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установить Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Добавить пользователя в группу docker
sudo usermod -aG docker $USER
```

### 2. Клонирование репозитория

```bash
# Клонировать репозиторий
git clone <repository-url> /opt/ringoo
cd /opt/ringoo

# Переключиться на production ветку
git checkout main
```

### 3. Настройка переменных окружения

```bash
# Скопировать шаблон
cp backend/.env.production backend/.env

# Отредактировать .env файл
nano backend/.env
```

**Обязательные переменные для production:**
```bash
DEBUG=False
SECRET_KEY=<сгенерируйте-безопасный-ключ>
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

DB_NAME=ringoo_prod
DB_USER=postgres
DB_PASSWORD=<надежный-пароль>
DB_HOST=db

REDIS_URL=redis://redis:6379/0

SENTRY_DSN=<ваш-sentry-dsn>
SENTRY_ENVIRONMENT=production

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Email настройки
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=<app-password>

# Maps API
YANDEX_MAPS_API_KEY=<ваш-ключ>
```

**Redis и идемпотентность заказов.** В production у всех воркеров приложения должен быть **один общий** экземпляр Redis: в `config/settings/base.py` кэш по умолчанию (`CACHES`) указывает на `REDIS_URL`. Создание заказа (`POST /api/v1/orders/`, `OrderListCreateView`) кладёт ключи заголовка `X-Idempotency-Key` в этот кэш. Если вместо Redis на каждом процессе использовать локальный кэш (например, LocMem), при нескольких воркерах gunicorn идемпотентность **не гарантируется** — возможны дубликаты заказов при повторе запроса. В development без Redis допустим LocMem (`config/settings/development.py`); для staging/production задавайте рабочий `REDIS_URL`.

**DEBUG, CORS и ALLOWED_HOSTS.** В production: `DEBUG=False`, `DJANGO_SETTINGS_MODULE=config.settings.production`. Не используйте `development.py` в проде: при `DEBUG=True` там включается `CORS_ALLOW_ALL_ORIGINS`. `ALLOWED_HOSTS` — непустой список доменов; пустая строка при `DEBUG=False` даёт ошибку при старте (`ImproperlyConfigured`). Платежи и PCI — `docs/PAYMENTS.md`.

### 4. Генерация SECRET_KEY

```bash
# Сгенерировать безопасный SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Сборка Docker образов

```bash
# Собрать production образы
docker-compose -f docker-compose.prod.yml build

# Или использовать Makefile
make build-prod
```

### 6. Запуск сервисов

```bash
# Запустить все сервисы
docker-compose -f docker-compose.prod.yml up -d

# Проверить статус
docker-compose -f docker-compose.prod.yml ps
```

### 7. Применение миграций

```bash
# Применить миграции
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# Создать суперпользователя
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# Собрать статические файлы
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### 8. Настройка Nginx

```bash
# Установить Nginx
sudo apt install nginx -y

# Создать конфигурацию
sudo nano /etc/nginx/sites-available/ringoo
```

**Конфигурация Nginx:**
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Редирект на HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Security headers (X-XSS-Protection устарел — не добавляем)
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Backend
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Static files
    location /static/ {
        alias /opt/ringoo/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /opt/ringoo/backend/media/;
        expires 7d;
    }
}
```

```bash
# Активировать конфигурацию
sudo ln -s /etc/nginx/sites-available/ringoo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 9. Настройка SSL (Let's Encrypt)

```bash
# Установить Certbot
sudo apt install certbot python3-certbot-nginx -y

# Получить сертификат
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Автоматическое обновление (уже настроено в cron)
sudo certbot renew --dry-run
```

## Мониторинг

### Health Checks

```bash
# Проверить health endpoint
curl https://your-domain.com/health/

# Должен вернуть:
# {"status": "healthy", "database": "ok", "cache": "ok"}
```

### Логи

```bash
# Просмотр логов всех сервисов
docker-compose -f docker-compose.prod.yml logs -f

# Логи конкретного сервиса
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f celery
```

### Мониторинг ресурсов

```bash
# Использование ресурсов
docker stats

# Дисковое пространство
df -h
docker system df
```

## Резервное копирование

### База данных

```bash
# Создать бэкап
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres ringoo_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановить из бэкапа
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres ringoo_prod < backup_20260205_120000.sql
```

### Автоматическое резервное копирование

Создайте cron задачу:
```bash
# Добавить в crontab
crontab -e

# Ежедневный бэкап в 2:00
0 2 * * * cd /opt/ringoo && docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres ringoo_prod > /backups/ringoo_$(date +\%Y\%m\%d).sql
```

## Обновление

```bash
# Остановить сервисы
docker-compose -f docker-compose.prod.yml down

# Получить последние изменения
git pull origin main

# Пересобрать образы
docker-compose -f docker-compose.prod.yml build

# Запустить сервисы
docker-compose -f docker-compose.prod.yml up -d

# Применить миграции
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# Собрать статические файлы
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Перезапустить сервисы
docker-compose -f docker-compose.prod.yml restart
```

## Откат (Rollback)

```bash
# Откатиться на предыдущую версию
git checkout <previous-commit-hash>

# Пересобрать и перезапустить
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Проблема: Сервисы не запускаются

```bash
# Проверить логи
docker-compose -f docker-compose.prod.yml logs

# Проверить статус
docker-compose -f docker-compose.prod.yml ps

# Пересоздать контейнеры
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Проблема: База данных недоступна

```bash
# Проверить подключение
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -c "SELECT 1;"

# Проверить логи БД
docker-compose -f docker-compose.prod.yml logs db
```

### Проблема: Статические файлы не загружаются

```bash
# Пересобрать статику
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Проверить права доступа
sudo chown -R www-data:www-data /opt/ringoo/backend/staticfiles/
```

---

**Дата создания:** 2026-02-05  
**Версия:** 1.0
