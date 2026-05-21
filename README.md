# 🛒 Ringoo - Интернет-магазин электроники

Современное высококонвертирующее веб-приложение для сети магазинов электроники "Ringoo".

## 📋 Описание проекта

Ringoo - это полнофункциональный интернет-магазин с системой лояльности, интеграцией с картами, блогом и новостями. Проект разработан с использованием современных технологий и лучших практик для обеспечения высокой производительности и отличного пользовательского опыта.

## 🚀 Технологический стек

### Backend
- **Django 5.0+** - основной фреймворк
- **Django REST Framework** - REST API
- **PostgreSQL 15+** - база данных
- **Redis 7+** - кэширование и очереди
- **Celery** - асинхронные задачи

### Frontend
- **Next.js 15** - React фреймворк с SSR/SSG
- **TypeScript** - типобезопасность
- **Tailwind CSS** - utility-first CSS
- **Framer Motion** - микроанимации
- **TanStack Query** - управление серверным состоянием

### Инфраструктура
- **Docker** - контейнеризация
- **Docker Compose** - оркестрация
- **Nginx** - reverse proxy
- **GitHub Actions** - CI/CD

## 📁 Структура проекта

```
ringoo/
├── backend/          # Django backend приложение
├── frontend/         # Next.js frontend приложение
├── docs/            # Документация проекта
├── docker/           # Docker конфигурации
├── PLAN.md          # Детальный план разработки
├── ARCHITECTURE.md   # Архитектурная документация
└── README.md        # Этот файл
```

## 🛠️ Быстрый старт

### Требования
- Python 3.11+
- Node.js 18+
- Docker и Docker Compose
- PostgreSQL 15+
- Redis 7+

### Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd ringoo
```

2. Настройте переменные окружения:
```bash
# Backend
cp backend/.env.example backend/.env.development
# Отредактируйте backend/.env.development при необходимости

# Frontend
cp frontend/.env.example frontend/.env.local
# Отредактируйте frontend/.env.local при необходимости
```

3. Настройте Docker-переменные фронта (опционально):
```bash
cp frontend/.env.docker.example frontend/.env.docker
```

4. Запустите весь стек через Docker Compose:
```bash
# Используя Makefile (рекомендуется)
make up

# Или напрямую
docker compose up -d --build
```

Сайт: **http://localhost:3000**, API: **http://localhost:8000**. Подробнее: [docs/DOCKER.md](./docs/DOCKER.md).

5. Выполните миграции:
```bash
# Используя Makefile
make migrate

# Или напрямую
docker-compose exec web python manage.py migrate
```

6. Создайте суперпользователя:
```bash
# Используя Makefile
make superuser

# Или напрямую
docker-compose exec web python manage.py createsuperuser
```

7. Проверьте статус сервисов:
```bash
make health
# Backend должен быть доступен на http://localhost:8000
```

### Разработка

#### Backend (через Docker - рекомендуется)
```bash
# Все команды выполняются через docker-compose
make shell          # Django shell
make migrate        # Применить миграции
make makemigrations # Создать миграции
make test           # Запустить тесты
make lint           # Проверить код линтерами
make logs           # Просмотр логов
```

#### Backend (локально, без Docker)

**Виртуальное окружение** изолирует зависимости проекта от системного Python — его нужно создавать и активировать перед работой.

```bash
cd backend

# Создать venv (один раз)
python -m venv venv

# Активировать venv
# Windows (cmd):     venv\Scripts\activate
# Windows (PowerShell): .\venv\Scripts\Activate.ps1
# Linux/macOS:       source venv/bin/activate

# Установить зависимости (в активированном venv)
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Запуск
python manage.py runserver
```

Миграции с активированным venv: `python manage.py migrate`

#### Frontend (через Docker — рекомендуется)
```bash
make up                 # поднимает frontend вместе с backend
make frontend-logs      # логи Next.js
make frontend-shell     # shell в контейнере
docker compose exec frontend npm run lint
docker compose exec frontend npm run build
```

Локально без Docker (по желанию): `cd frontend && npm install && npm run dev`

#### Полезные команды Makefile
```bash
make help           # Показать все доступные команды
make up             # Запустить все сервисы
make down           # Остановить все сервисы
make restart        # Перезапустить сервисы
make logs           # Показать логи
make clean          # Очистить volumes и кэш
```

## 📚 Документация

- [План разработки](./PLAN.md) - детальный атомарный план
- [Архитектура](./docs/ARCHITECTURE.md) - архитектурный анализ
- [API Документация](./docs/API.md) - описание API endpoints
- [Безопасность](./docs/SECURITY.md) - чеклист и реализация безопасности
- [Юридическое соответствие](./docs/LEGAL.md) - 152-ФЗ, GDPR, оферта, реквизиты
- [Юзабилити и UX](./docs/UX.md) - мобильная версия, скелетоны, сообщения об ошибках
- [Резервное копирование](./docs/BACKUP.md) - ежедневные бэкапы БД и медиа, восстановление за час
- [Для клиента (руководитель)](./docs/ДЛЯ_КЛИЕНТА_НАРИНА.md) - что сделано и как всё работает, простым языком

## 🧪 Тестирование

```bash
# Backend тесты
cd backend
pytest

# Frontend тесты
cd frontend
npm test
```

## 🚀 Деплой

Инструкции по деплою находятся в [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)

## 📝 Лицензия

MIT License - см. [LICENSE](./LICENSE) файл

## 👥 Команда

Проект разработан для сети магазинов "Ringoo"

## 📞 Контакты

Для вопросов и предложений создавайте Issues в репозитории.

---

**Версия:** 1.0.0  
**Дата:** 2026-02-05
