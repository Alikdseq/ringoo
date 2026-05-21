# Тестирование подключения к Redis

## Шаги для тестирования подключения к Redis

### Шаг 1: Запустить Redis через Docker Compose

```bash
# Запустить только Redis (без других сервисов)
docker-compose up -d redis

# Или запустить все сервисы
make up
```

**Проверка:** Убедитесь, что контейнер запущен:
```bash
docker-compose ps
# Должен показать статус "Up" и "healthy" для ringoo_redis
```

### Шаг 2: Проверить healthcheck контейнера

```bash
# Проверить статус healthcheck
docker inspect ringoo_redis | grep -A 10 Health

# Или проверить логи
docker-compose logs redis
```

**Ожидаемый результат:** Healthcheck должен показывать "healthy" через несколько секунд после запуска.

### Шаг 3: Тестирование подключения через redis-cli

```bash
# Подключиться к Redis через redis-cli
make redis-cli
# Или: docker-compose exec redis redis-cli

# В redis-cli выполните команды:
PING
# Должен вернуть: PONG

INFO
# Покажет информацию о Redis

KEYS *
# Покажет все ключи (пока пусто)

EXIT
# Выйти из redis-cli
```

**Ожидаемый результат:**
- Команда `PING` должна вернуть `PONG`
- Информация о Redis должна отображаться
- Версия Redis должна быть 7.x

### Шаг 4: Тестирование подключения через Django

```bash
# Запустить Django shell
make shell

# Или напрямую через docker-compose
docker-compose exec web python manage.py shell
```

**В Django shell выполните:**
```python
from django.core.cache import cache

# Проверить подключение к кэшу
cache.set('test_key', 'test_value', timeout=10)
print(cache.get('test_key'))  # Должно вернуть 'test_value'

# Проверить настройки
from django.conf import settings
print(f"Cache backend: {settings.CACHES['default']['BACKEND']}")
print(f"Cache location: {settings.CACHES['default']['LOCATION']}")
print(f"Session engine: {settings.SESSION_ENGINE}")
print(f"Celery broker: {settings.CELERY_BROKER_URL}")
```

**Ожидаемый результат:**
- `cache.set()` и `cache.get()` должны работать без ошибок
- Настройки должны указывать на Redis

### Шаг 5: Тестирование через Python скрипт

```bash
# Запустить автоматический тест
make redis-test

# Или напрямую
docker-compose exec web python test_redis_connection.py
```

**Ожидаемый результат:**
- Все проверки должны пройти успешно
- Должна отображаться версия Redis 7.x
- Кэш должен работать (запись/чтение/удаление)
- Celery конфигурация должна быть правильной

### Шаг 6: Проверка через health endpoint

```bash
# Убедитесь что web сервис запущен
docker-compose up -d web

# Проверить health endpoint (должен проверить Redis)
curl http://localhost:8000/health/

# Или через браузер
# Откройте: http://localhost:8000/health/
```

**Ожидаемый результат:**
```json
{
  "status": "healthy",
  "database": "ok",
  "cache": "ok"
}
```

### Шаг 7: Проверка переменных окружения

```bash
# Проверить переменные окружения в контейнере web
docker-compose exec web env | grep REDIS

# Должны быть видны:
# REDIS_URL=redis://redis:6379/0
# CELERY_BROKER_URL=redis://redis:6379/0
# CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### Шаг 8: Проверка логов при подключении

```bash
# Просмотр логов Redis
docker-compose logs redis | tail -20

# Просмотр логов Django (если есть ошибки подключения)
docker-compose logs web | grep -i redis
```

**Ожидаемый результат:**
- В логах Redis не должно быть ошибок
- В логах Django не должно быть ошибок подключения

### Шаг 9: Проверка работы кэша

```bash
# Запустить Django shell
make shell
```

**В Django shell:**
```python
from django.core.cache import cache

# Тест записи и чтения
cache.set('test', 'value', 60)
print(cache.get('test'))  # Должно вернуть 'value'

# Тест удаления
cache.delete('test')
print(cache.get('test'))  # Должно вернуть None

# Тест множественных операций
cache.set_many({'key1': 'value1', 'key2': 'value2'})
print(cache.get_many(['key1', 'key2']))
cache.delete_many(['key1', 'key2'])
```

### Шаг 10: Проверка работы сессий (если используется Redis)

```python
# В Django shell
from django.contrib.sessions.backends.cache import SessionStore

# Создать тестовую сессию
session = SessionStore()
session['test_key'] = 'test_value'
session.save()

# Проверить что сессия сохранена
session_key = session.session_key
print(f"Session key: {session_key}")

# Загрузить сессию
loaded_session = SessionStore(session_key)
print(f"Loaded value: {loaded_session.get('test_key')}")
```

---

## Быстрая проверка (все шаги одной командой)

```bash
# Автоматический тест
make redis-test

# Или простая проверка ping
make redis-ping
# Должен вернуть: PONG
```

---

## Устранение проблем

### Проблема: Контейнер не запускается
```bash
# Проверить логи
docker-compose logs redis

# Пересоздать контейнер
docker-compose down
docker-compose up -d redis
```

### Проблема: Ошибка подключения "connection refused"
```bash
# Проверить что контейнер запущен
docker-compose ps

# Проверить что порт не занят
netstat -an | grep 6379

# Проверить healthcheck
docker inspect ringoo_redis | grep -A 5 Health
```

### Проблема: Ошибка "No module named 'django_redis'"
```bash
# Установить зависимости
docker-compose exec web pip install django-redis

# Или пересобрать контейнер
docker-compose build web
docker-compose up -d web
```

### Проблема: Кэш не работает
```bash
# Проверить настройки в settings/base.py
# Убедиться что CACHES настроен правильно

# Проверить переменные окружения
docker-compose exec web env | grep REDIS

# Проверить подключение напрямую
docker-compose exec web python -c "from django.core.cache import cache; cache.set('test', 'ok'); print(cache.get('test'))"
```

---

## Проверка конфигурации

### Что должно быть настроено:

1. **Redis в docker-compose.yml:**
   - Сервис `redis` с образом `redis:7-alpine`
   - Healthcheck настроен
   - Volume для персистентности данных

2. **Celery broker URL:**
   - `CELERY_BROKER_URL` в `settings/base.py`
   - Использует `REDIS_URL` из переменных окружения

3. **Кэш backend:**
   - `CACHES['default']` использует `django_redis.cache.RedisCache`
   - `LOCATION` указывает на Redis

4. **Session backend:**
   - `SESSION_ENGINE = 'django.contrib.sessions.backends.cache'`
   - `SESSION_CACHE_ALIAS = 'sessions'`
   - `CACHES['sessions']` использует Redis

---

## Следующие шаги после успешного тестирования

После успешного тестирования подключения:

1. ✅ Отметить задачу 0.4.2 как выполненную
2. Перейти к задаче 0.4.3 (Настройка Celery - уже частично выполнена)
3. Затем к задаче 0.4.3 (Создание начальных миграций)

---

**Дата создания:** 2026-02-05  
**Версия:** 1.0
