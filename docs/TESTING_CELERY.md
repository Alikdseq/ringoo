# Тестирование Celery

## Шаги для тестирования Celery

### Шаг 1: Запустить Celery Worker

```bash
# Запустить Celery worker
docker-compose up -d celery

# Или запустить все сервисы
make up
```

**Проверка:** Убедитесь, что контейнер запущен:
```bash
docker-compose ps
# Должен показать статус "Up" для ringoo_celery
```

### Шаг 2: Проверить логи Celery

```bash
# Просмотр логов в реальном времени
make celery-logs

# Или напрямую
docker-compose logs -f celery
```

**Ожидаемый результат:**
- Должны быть видны сообщения о подключении к broker
- Должны быть видны зарегистрированные задачи
- Не должно быть ошибок подключения

Пример успешного запуска:
```
celery@ringoo_celery v5.3.4 (emerald-rush)

[config]
.> app:         ringoo:0x...
.> transport:   redis://redis:6379/0
.> results:     redis://redis:6379/0
.> concurrency: 4 (prefork)
.> task events: OFF (enable -E to monitor tasks in real-time)

[queues]
.> celery           exchange=celery(direct) key=celery

[tasks]
  . apps.users.tasks.test_celery_task
  . celery.accumulate
  . celery.backend_cleanup
  ...
```

### Шаг 3: Тестирование через Python скрипт

```bash
# Запустить автоматический тест
make celery-test

# Или напрямую
docker-compose exec web python test_celery.py
```

**Ожидаемый результат:**
- Конфигурация должна быть правильной
- Подключение к broker должно быть успешным
- Задачи должны быть зарегистрированы

### Шаг 4: Тестирование выполнения задачи через Django shell

```bash
# Запустить Django shell
make shell

# Или напрямую
docker-compose exec web python manage.py shell
```

**В Django shell выполните:**
```python
from apps.users.tasks import test_celery_task

# Асинхронное выполнение задачи
result = test_celery_task.delay()
print(f"Task ID: {result.id}")

# Проверить статус задачи
print(f"Status: {result.status}")

# Получить результат (будет ждать выполнения)
print(f"Result: {result.get(timeout=10)}")
```

**Ожидаемый результат:**
- Задача должна быть отправлена в очередь
- Статус должен измениться с PENDING на SUCCESS
- Результат должен быть получен

### Шаг 5: Проверка активных задач

```bash
# Проверить активные задачи
make celery-inspect

# Или напрямую
docker-compose exec celery celery -A config.celery inspect active
```

**Ожидаемый результат:**
- Если есть активные задачи, они будут показаны
- Если задач нет, будет пустой список

### Шаг 6: Проверка зарегистрированных задач

```bash
# Открыть Celery shell
make celery-shell

# Или напрямую
docker-compose exec celery celery -A config.celery shell
```

**В Celery shell:**
```python
# Показать все зарегистрированные задачи
app.tasks.keys()

# Показать информацию о конкретной задаче
app.tasks['apps.users.tasks.test_celery_task']
```

### Шаг 7: Тестирование через Celery shell

```bash
make celery-shell
```

**В Celery shell выполните:**
```python
from apps.users.tasks import test_celery_task

# Выполнить задачу
result = test_celery_task.delay()

# Проверить результат
result.ready()  # True если выполнена
result.get()    # Получить результат
```

### Шаг 8: Мониторинг задач в реальном времени

```bash
# Запустить worker с событиями
docker-compose exec celery celery -A config.celery worker --loglevel=info -E

# В другом терминале выполнить задачу
docker-compose exec web python manage.py shell
```

**В Django shell:**
```python
from apps.users.tasks import test_celery_task
test_celery_task.delay()
```

**В логах worker должны появиться сообщения:**
```
[2026-02-05 12:00:00,000: INFO/MainProcess] Task apps.users.tasks.test_celery_task[xxx] received
[2026-02-05 12:00:00,001: INFO/MainProcess] Task apps.users.tasks.test_celery_task[xxx] succeeded in 0.001s: 'Celery is working correctly!'
```

---

## Быстрая проверка

```bash
# 1. Запустить worker
docker-compose up -d celery

# 2. Проверить логи (должны быть без ошибок)
docker-compose logs celery | tail -20

# 3. Запустить тест
make celery-test

# 4. Выполнить тестовую задачу
docker-compose exec web python manage.py shell
```

**В shell:**
```python
from apps.users.tasks import test_celery_task
result = test_celery_task.delay()
print(result.get(timeout=5))  # Должно вернуть: "Celery is working correctly!"
```

---

## Устранение проблем

### Проблема: Worker не запускается

```bash
# Проверить логи
docker-compose logs celery

# Проверить что Redis доступен
docker-compose exec redis redis-cli ping
# Должен вернуть: PONG

# Пересоздать контейнер
docker-compose restart celery
```

### Проблема: Ошибка подключения к broker

```bash
# Проверить переменные окружения
docker-compose exec celery env | grep REDIS

# Проверить что Redis запущен
docker-compose ps redis

# Проверить настройки в settings/base.py
# CELERY_BROKER_URL должен быть правильным
```

### Проблема: Задачи не выполняются

```bash
# Проверить что worker запущен
docker-compose ps celery

# Проверить логи worker
docker-compose logs celery

# Проверить что задачи зарегистрированы
docker-compose exec celery celery -A config.celery inspect registered
```

### Проблема: Задачи выполняются синхронно

```bash
# Убедитесь что worker запущен
docker-compose up -d celery

# Проверьте что используется .delay() или .apply_async()
# Не используйте .apply() - это синхронное выполнение
```

---

## Проверка конфигурации

### Что должно быть настроено:

1. **config/celery.py:**
   - Celery app создан
   - Настройки загружаются из Django settings
   - Автообнаружение задач включено

2. **config/__init__.py:**
   - Celery app импортирован при старте Django

3. **settings/base.py:**
   - `CELERY_BROKER_URL` настроен
   - `CELERY_RESULT_BACKEND` настроен
   - `CELERY_TIMEZONE` настроен

4. **docker-compose.yml:**
   - Сервис `celery` настроен
   - Зависимости от db, redis, web настроены

---

## Примеры использования

### Создание задачи

```python
# В apps/users/tasks.py
from celery import shared_task

@shared_task
def send_notification(user_id, message):
    # Ваша логика здесь
    pass
```

### Вызов задачи

```python
# Синхронно (не рекомендуется в production)
from apps.users.tasks import send_notification
result = send_notification(user_id=1, message="Hello")

# Асинхронно (рекомендуется)
result = send_notification.delay(user_id=1, message="Hello")

# С отложенным выполнением
from datetime import datetime, timedelta
eta = datetime.utcnow() + timedelta(seconds=10)
result = send_notification.apply_async(
    args=[1, "Hello"],
    eta=eta
)
```

---

**Дата создания:** 2026-02-05  
**Версия:** 1.0
