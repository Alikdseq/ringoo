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
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

3. Запустите через Docker Compose:
```bash
docker-compose up -d
```

4. Выполните миграции:
```bash
docker-compose exec web python manage.py migrate
```

5. Создайте суперпользователя:
```bash
docker-compose exec web python manage.py createsuperuser
```

### Разработка

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 📚 Документация

- [План разработки](./PLAN.md) - детальный атомарный план
- [Архитектура](./ARCHITECTURE.md) - архитектурный анализ
- [API Документация](./docs/API.md) - описание API endpoints

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
