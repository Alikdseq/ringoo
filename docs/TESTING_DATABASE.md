# Тестирование подключения к PostgreSQL

## Шаги для тестирования подключения к базе данных

### Шаг 1: Запустить PostgreSQL через Docker Compose

```bash
# Запустить только PostgreSQL (без других сервисов)
docker-compose up -d db

# Или запустить все сервисы
make up
```

**Проверка:** Убедитесь, что контейнер запущен:
```bash
docker-compose ps
# Должен показать статус "Up" для ringoo_db
```

### Шаг 2: Проверить healthcheck контейнера

```bash
# Проверить статус healthcheck
docker inspect ringoo_db | grep -A 10 Health

# Или проверить логи
docker-compose logs db
```

**Ожидаемый результат:** Healthcheck должен показывать "healthy" через несколько секунд после запуска.

### Шаг 3: Тестирование подключения через psql (внутри контейнера)

```bash
# Подключиться к PostgreSQL через psql внутри контейнера
docker-compose exec db psql -U postgres -d ringoo

# Или использовать Makefile команду
make db-shell
```

**Проверка:** После подключения выполните SQL команды:
```sql
-- Проверить версию PostgreSQL
SELECT version();

-- Проверить список баз данных
\l

-- Проверить текущую базу данных
SELECT current_database();

-- Выйти из psql
\q
```

**Ожидаемый результат:**
- Версия PostgreSQL должна быть 15.x
- База данных `ringoo` должна существовать
- Подключение должно быть успешным

### Шаг 4: Тестирование подключения через Django

```bash
# Запустить Django shell
make shell

# Или напрямую через docker-compose
docker-compose exec web python manage.py shell
```

**В Django shell выполните:**
```python
from django.db import connection

# Проверить подключение к БД
connection.ensure_connection()

# Проверить настройки подключения
from django.conf import settings
print(f"Database: {settings.DATABASES['default']['NAME']}")
print(f"Host: {settings.DATABASES['default']['HOST']}")
print(f"User: {settings.DATABASES['default']['USER']}")

# Выполнить простой SQL запрос
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT version();")
print(cursor.fetchone())

# Проверить что таблицы еще не созданы (до миграций)
cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public';
""")
print(cursor.fetchall())
```

**Ожидаемый результат:**
- `connection.ensure_connection()` не должно вызывать ошибок
- Должны отображаться правильные настройки БД
- SQL запрос должен выполниться успешно

### Шаг 5: Тестирование через Python скрипт

Создайте временный скрипт для проверки:

```bash
# Создать файл test_db_connection.py в backend/
cat > backend/test_db_connection.py << 'EOF'
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.db import connection
from django.conf import settings

def test_connection():
    try:
        # Проверка подключения
        connection.ensure_connection()
        print("✅ Подключение к БД успешно!")
        
        # Проверка настроек
        db = settings.DATABASES['default']
        print(f"📊 База данных: {db['NAME']}")
        print(f"🖥️  Хост: {db['HOST']}")
        print(f"👤 Пользователь: {db['USER']}")
        print(f"🔌 Порт: {db['PORT']}")
        
        # Выполнение тестового запроса
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"📦 Версия PostgreSQL: {version}")
        
        # Проверка списка баз данных
        cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        databases = [row[0] for row in cursor.fetchall()]
        print(f"🗄️  Доступные базы данных: {', '.join(databases)}")
        
        print("\n✅ Все проверки пройдены успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)
EOF

# Запустить скрипт
docker-compose exec web python test_db_connection.py

# Удалить скрипт после проверки
rm backend/test_db_connection.py
```

**Ожидаемый результат:**
- Все проверки должны пройти успешно
- Должна отображаться версия PostgreSQL 15.x
- База данных `ringoo` должна быть в списке

### Шаг 6: Тестирование через Django management команду

```bash
# Проверить подключение через Django
docker-compose exec web python manage.py check --database default

# Проверить что миграции могут быть применены (пока без применения)
docker-compose exec web python manage.py showmigrations
```

**Ожидаемый результат:**
- `check --database default` не должно показывать ошибок
- `showmigrations` должен выполниться без ошибок (даже если миграций еще нет)

### Шаг 7: Тестирование подключения с хоста (опционально)

Если PostgreSQL доступен на порту 5432:

```bash
# Проверить доступность порта
netstat -an | grep 5432
# Или на Windows
netstat -an | findstr 5432

# Подключиться с хоста (если установлен psql)
psql -h localhost -p 5432 -U postgres -d ringoo
```

**Примечание:** Для подключения с хоста используйте пароль из `.env.development` (по умолчанию: `postgres`)

### Шаг 8: Проверка через health endpoint

```bash
# Запустить web сервис
docker-compose up -d web

# Проверить health endpoint (должен проверить БД)
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

### Шаг 9: Проверка переменных окружения

```bash
# Проверить переменные окружения в контейнере web
docker-compose exec web env | grep DB_

# Должны быть видны:
# DB_NAME=ringoo
# DB_USER=postgres
# DB_PASSWORD=postgres
# DB_HOST=db
# DB_PORT=5432
```

### Шаг 10: Проверка логов при подключении

```bash
# Просмотр логов PostgreSQL
docker-compose logs db | tail -20

# Просмотр логов Django (если есть ошибки подключения)
docker-compose logs web | grep -i database
```

**Ожидаемый результат:**
- В логах PostgreSQL не должно быть ошибок
- В логах Django не должно быть ошибок подключения

---

## Быстрая проверка (все шаги одной командой)

```bash
# Создать и запустить скрипт проверки
cat > backend/quick_db_test.py << 'EOF'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.db import connection
from django.conf import settings

try:
    connection.ensure_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT version();")
    print("✅ PostgreSQL подключение успешно!")
    print(f"Версия: {cursor.fetchone()[0]}")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    exit(1)
EOF

docker-compose exec web python quick_db_test.py
rm backend/quick_db_test.py
```

---

## Устранение проблем

### Проблема: Контейнер не запускается
```bash
# Проверить логи
docker-compose logs db

# Пересоздать контейнер
docker-compose down
docker-compose up -d db
```

### Проблема: Ошибка подключения "connection refused"
```bash
# Проверить что контейнер запущен
docker-compose ps

# Проверить что порт не занят
netstat -an | grep 5432

# Проверить healthcheck
docker inspect ringoo_db | grep -A 5 Health
```

### Проблема: UnicodeDecodeError при `python manage.py migrate` (Windows, кириллица в пути)

Ошибка вида `'utf-8' codec can't decode byte 0xdd in position 47` часто возникает, когда проект лежит в пути с кириллицей (например `C:\Users\Алихан\Desktop\Ringoo`): libpq/psycopg2 при подключении может обращаться к путям в кодировке Windows (CP1251).

**Что сделать:**

1. **Запуск с нужными переменными окружения (рекомендуется)**  
   В папке `backend` выполните:
   ```cmd
   set PGCLIENTENCODING=UTF8
   set PGPASSFILE=
   set PYTHONUTF8=1
   python manage.py migrate
   ```
   Или используйте готовый скрипт: `backend\run_migrate.bat`.

2. **Проверить, откуда читается .env**  
   Django ищет `backend\.env.development` или `.env.development` в корне репозитория. Сохраните файл в кодировке **UTF-8** (Без BOM). В параметрах БД используйте только латиницу (например пароль `postgres`).  
   **Если запускаете миграции с ПК (не из Docker):** в `.env.development` укажите `DB_HOST=localhost` (а не `db`).

3. **Временный обход: путь без кириллицы**  
   Скопируйте проект в каталог только с латиницей, например `C:\Projects\Ringoo`, и запускайте миграции оттуда.

В коде уже заданы `PGCLIENTENCODING` и `PGPASSFILE` при запуске на Windows; если ошибка остаётся, используйте пункт 1 или 3.

### Проблема: Ошибка аутентификации
```bash
# Проверить переменные окружения
docker-compose exec web env | grep DB_

# Убедиться что пароли совпадают в:
# - docker-compose.yml
# - .env.development
# - settings/development.py
```

### Проблема: База данных не существует
```bash
# Создать базу данных вручную
docker-compose exec db psql -U postgres -c "CREATE DATABASE ringoo;"

# Или изменить DB_NAME в .env.development на существующую БД
```

---

## Следующие шаги после успешного тестирования

После успешного тестирования подключения:

1. ✅ Отметить задачу 0.4.1 как выполненную
2. Перейти к задаче 0.4.2 (Настройка Redis)
3. Затем к задаче 0.4.3 (Создание начальных миграций)

---

**Дата создания:** 2026-02-05  
**Версия:** 1.0
