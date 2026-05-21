# Настройка Sentry для мониторинга ошибок

## Что такое Sentry?

Sentry - это платформа для мониторинга ошибок и производительности приложений. Она автоматически отслеживает исключения, ошибки и проблемы производительности в реальном времени.

## Регистрация на Sentry

### Вариант 1: Использование Sentry.io (облачный сервис)

1. Перейдите на https://sentry.io
2. Зарегистрируйтесь или войдите в аккаунт
3. Создайте новый проект:
   - Выберите платформу: **Django**
   - Название проекта: `ringoo`
   - Организация: выберите или создайте новую
4. Скопируйте **DSN** (Data Source Name)
5. Добавьте DSN в `.env.development`:
   ```
   SENTRY_DSN=https://your-dsn@sentry.io/project-id
   SENTRY_ENVIRONMENT=development
   ```

### Вариант 2: Self-hosted Sentry (опционально)

Если вы хотите использовать собственный сервер Sentry:
1. Установите Sentry согласно официальной документации
2. Получите DSN с вашего сервера
3. Добавьте в `.env.development`

## Конфигурация

### Переменные окружения

Добавьте в `backend/.env.development`:

```bash
# Sentry Configuration
SENTRY_DSN=https://your-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=development
SENTRY_RELEASE=1.0.0  # Опционально - версия приложения
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% запросов для трейсинга
```

### Production настройки

В `backend/.env.production`:

```bash
SENTRY_DSN=https://your-production-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=1.0.0
SENTRY_TRACES_SAMPLE_RATE=0.1
```

## Безопасность

### Фильтрация чувствительных данных

Sentry автоматически фильтрует следующие чувствительные поля:
- `password`, `password1`, `password2`
- `secret`, `secret_key`, `api_key`, `api_secret`
- `token`, `access_token`, `refresh_token`
- `authorization`, `auth`
- `credit_card`, `card_number`, `cvv`
- `ssn`, `social_security_number`

Эти данные будут заменены на `[FILTERED]` перед отправкой в Sentry.

### Дополнительные настройки безопасности

- `send_default_pii=False` - не отправлять персональные данные по умолчанию
- Фильтрация email и username пользователей
- Фильтрация cookies и query parameters

## Тестирование

### Автоматический тест

```bash
# Запустить тест Sentry
docker-compose exec web python test_sentry.py
```

### Ручное тестирование

```bash
# Запустить Django shell
make shell
```

**В Django shell:**
```python
import sentry_sdk

# Отправить тестовое сообщение
sentry_sdk.capture_message("Test message from Ringoo", level="info")

# Отправить тестовое исключение
try:
    raise ValueError("Test exception")
except Exception as e:
    sentry_sdk.capture_exception(e)
```

### Проверка в Sentry Dashboard

1. Откройте https://sentry.io (или ваш self-hosted сервер)
2. Перейдите в проект `ringoo`
3. Проверьте что тестовые сообщения появились
4. Убедитесь что чувствительные данные отфильтрованы

## Интеграции

Sentry автоматически интегрируется с:

1. **Django Integration:**
   - Отслеживание исключений Django
   - Трейсинг HTTP запросов
   - Отслеживание middleware

2. **Celery Integration:**
   - Отслеживание ошибок в Celery задачах
   - Трейсинг выполнения задач

3. **Logging Integration:**
   - Автоматическая отправка логов уровня ERROR и выше
   - Интеграция с Django logging

## Что отслеживается

### Автоматически отслеживается:

- Все необработанные исключения
- Ошибки уровня ERROR и выше в логах
- Ошибки в Celery задачах
- HTTP ошибки (500, 502, 503, etc.)

### Игнорируется:

- `KeyboardInterrupt` (Ctrl+C)
- `Http404` (страница не найдена)
- `Http403` (доступ запрещен)

## Мониторинг производительности

Sentry также отслеживает производительность:

- Время выполнения запросов
- Медленные запросы (>1 секунды)
- N+1 запросы к БД
- Производительность Celery задач

## Алерты и уведомления

В Sentry можно настроить:

1. **Email уведомления** при новых ошибках
2. **Slack интеграцию** для команды
3. **Telegram бот** для критичных ошибок
4. **Webhooks** для интеграции с другими системами

## Best Practices

1. **Не отправляйте тестовые ошибки в production**
   - Используйте отдельный проект для development
   - Или отключайте Sentry в тестах

2. **Настройте релизы**
   - Указывайте версию приложения в `SENTRY_RELEASE`
   - Это поможет отслеживать ошибки по версиям

3. **Используйте теги**
   - Добавляйте теги для группировки ошибок
   - Например: `environment`, `user_id`, `feature`

4. **Настройте sample rate**
   - Для production: `0.1` (10% запросов)
   - Для development: можно выше для тестирования

## Отключение Sentry

Если нужно временно отключить Sentry:

```bash
# В .env.development
SENTRY_DSN=
```

Или закомментируйте блок Sentry в `settings/base.py`.

## Troubleshooting

### Проблема: Ошибки не отправляются

```bash
# Проверьте DSN
docker-compose exec web env | grep SENTRY_DSN

# Проверьте логи
docker-compose logs web | grep -i sentry

# Проверьте подключение к интернету
docker-compose exec web ping -c 3 sentry.io
```

### Проблема: Слишком много событий

```bash
# Уменьшите traces_sample_rate
SENTRY_TRACES_SAMPLE_RATE=0.01  # 1% вместо 10%

# Или отключите трейсинг
SENTRY_TRACES_SAMPLE_RATE=0
```

### Проблема: Чувствительные данные попадают в Sentry

```bash
# Проверьте функцию before_send в settings/base.py
# Убедитесь что все нужные поля добавлены в sensitive_fields
```

---

**Дата создания:** 2026-02-05  
**Версия:** 1.0
