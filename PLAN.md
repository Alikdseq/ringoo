# 🚀 ДЕТАЛЬНЫЙ ПЛАН РАЗРАБОТКИ RINGOO

## Интернет-магазин электроники с высоконагруженной архитектурой

---

## 📋 ОГЛАВЛЕНИЕ

1. [ЭТАП 0: Подготовка инфраструктуры](#этап-0-подготовка-инфраструктуры)
2. [ЭТАП 1: Backend - Sprint A - Базовые модели и API](#этап-1-backend---sprint-a)
3. [ЭТАП 2: Backend - Sprint B - Продвинутые функции](#этап-2-backend---sprint-b)
4. [ЭТАП 3: Frontend - Sprint C - Next.js приложение](#этап-3-frontend---sprint-c)
5. [ЭТАП 4: Интеграции и продвинутые функции](#этап-4-интеграции-и-продвинутые-функции)
6. [ЭТАП 5: QA, Тестирование и Релиз](#этап-5-qa-тестирование-и-релиз)

---

## 🎯 АРХИТЕКТУРНОЕ РЕШЕНИЕ

### Выбор стека технологий

**Backend:**
- **Django 5.0+** - Выбор обоснован:
  - Зрелый фреймворк с богатой экосистемой
  - Отличная ORM для работы с PostgreSQL
  - Встроенная админ-панель для управления контентом
  - Поддержка асинхронности (Django Channels для WebSocket)
  - Гибкая система миграций
  - Отличная документация и сообщество
- **Django REST Framework** - для построения RESTful API
- **PostgreSQL 15+** - реляционная БД для сложных запросов
- **Redis 7+** - кэширование и Celery broker
- **Celery** - асинхронные задачи (SMS, email, уведомления)

**Frontend:**
- **Next.js 16 (App Router), React 19** — SSR/SSG для SEO и производительности (версии как в `frontend/package.json`)
- **TypeScript** - типобезопасность
- **Tailwind CSS** - utility-first CSS фреймворк
- **Framer Motion** - микроанимации 60 FPS
- **TanStack Query** - управление серверным состоянием
- **Zustand** - клиентское состояние

**Инфраструктура:**
- **Docker & Docker Compose** - контейнеризация
- **Nginx** - reverse proxy и статика
- **GitHub Actions** - CI/CD
- **Sentry** - мониторинг ошибок

### Архитектурный паттерн

**Monolith → Microservices-ready:**
- Четкое разделение на приложения (apps/)
- Сервисный слой (services/) для бизнес-логики
- Селекторы (selectors/) для оптимизированных запросов
- Готовность к выделению сервисов при необходимости

---

## ЭТАП 0: ПОДГОТОВКА ИНФРАСТРУКТУРЫ

### 📦 0.1 Инициализация проекта и репозитория

**Задача 0.1.1:** Создать структуру monorepo
- [x] Создать корневую директорию `ringoo/`
- [x] Создать поддиректории: `backend/`, `frontend/`, `docs/`, `docker/`
- [x] Инициализировать git репозиторий: `git init`
- [x] Создать `.gitignore` для Python, Node.js, Docker
- [x] Создать `README.md` с описанием проекта
- [x] Создать `LICENSE` файл

**Задача 0.1.2:** Настроить Git Flow
- [x] Создать ветку `develop`
- [x] Создать ветку `staging`
- [x] Создать ветку `main` (production)
- [x] Настроить правила защиты веток (если GitHub/GitLab)
- [x] Создать шаблон для commit messages (conventional commits)
- [x] Настроить `.github/PULL_REQUEST_TEMPLATE.md`

**Задача 0.1.3:** Настроить базовые CI/CD pipeline
- [x] Создать `.github/workflows/backend-ci.yml`
- [x] Создать `.github/workflows/frontend-ci.yml`
- [x] Настроить линтеры для Python (black, isort, flake8, mypy)
- [x] Настроить линтеры для TypeScript (ESLint, Prettier)
- [x] Добавить проверку на PR (lint + tests)
- [x] Настроить автоматический запуск тестов

### 🐳 0.2 Docker и локальная среда разработки

**Задача 0.2.1:** Создать Dockerfile для backend
- [x] Создать `backend/Dockerfile` (multi-stage build)
- [x] Настроить Python 3.11-slim базовый образ
- [x] Оптимизировать слои кэширования (requirements.txt отдельно)
- [x] Добавить healthcheck
- [x] Настроить non-root user для безопасности
- [x] Настроить рабочий каталог

**Задача 0.2.2:** Создать docker-compose для разработки
- [x] Создать `docker-compose.yml` в корне
- [x] Настроить сервис `web` (Django)
- [x] Настроить сервис `db` (PostgreSQL 15)
- [x] Настроить сервис `redis` (Redis 7)
- [x] Настроить сервис `celery` (worker)
- [x] Настроить сервис `celery-beat` (scheduler, опционально)
- [x] Настроить volumes для данных и кода
- [x] Настроить networks для изоляции
- [x] Настроить environment variables

**Задача 0.2.3:** Создать файлы окружения
- [x] Создать `backend/.env.example` с всеми переменными
- [x] Создать `backend/.env.development`
- [x] Создать `backend/.env.production` (шаблон)
- [x] Создать `frontend/.env.example`
- [x] Создать `frontend/.env.local` (для разработки)
- [x] Добавить инструкции по настройке в README

**Задача 0.2.4:** Настроить Makefile для удобства
- [x] Создать `Makefile` с командами:
  - `make up` - запуск docker-compose
  - `make down` - остановка
  - `make migrate` - миграции
  - `make shell` - Django shell
  - `make test` - запуск тестов
  - `make lint` - линтеры
  - `make frontend-dev` - запуск Next.js dev server
  - `make build` - сборка production образов

### 🔧 0.3 Настройка Django проекта

**Задача 0.3.1:** Инициализировать Django проект
- [x] Создать виртуальное окружение (или использовать Docker)
- [x] Установить Django 5.0+ и зависимости
- [x] Создать проект: `django-admin startproject config backend/`
- [x] Настроить базовую структуру приложений в `backend/apps/`
- [x] Создать структуру: `apps/users/`, `apps/products/`, `apps/orders/`, `apps/stores/`, `apps/content/`, `apps/cart/`, `apps/bonus/`

**Задача 0.3.2:** Настроить settings.py
- [x] Разделить на `base.py`, `development.py`, `production.py`, `test.py`
- [x] Настроить `SECRET_KEY` из переменных окружения
- [x] Настроить `DEBUG`, `ALLOWED_HOSTS`
- [x] Настроить `DATABASES` (PostgreSQL)
- [x] Настроить `AUTH_USER_MODEL = 'users.CustomUser'`
- [x] Настроить `INSTALLED_APPS` (базовые + наши)
- [x] Настроить `MIDDLEWARE`
- [x] Настроить `STATIC_URL`, `MEDIA_URL`, `STATIC_ROOT`, `MEDIA_ROOT`
- [x] Настроить `TIME_ZONE`, `LANGUAGE_CODE`
- [x] Добавить `CORS` настройки для фронтенда
- [x] Настроить `REST_FRAMEWORK` settings

**Задача 0.3.3:** Настроить базовые зависимости
- [x] Создать `backend/requirements.txt`
- [x] Добавить: `Django>=5.0,<6.0`
- [x] Добавить: `djangorestframework>=3.14`
- [x] Добавить: `djangorestframework-simplejwt>=5.2`
- [x] Добавить: `psycopg2-binary>=2.9`
- [x] Добавить: `celery[redis]>=5.3`
- [x] Добавить: `redis>=5.0`
- [x] Добавить: `python-dotenv>=1.0`
- [x] Добавить: `drf-spectacular>=0.26` (OpenAPI)
- [x] Добавить: `django-cors-headers>=4.2`
- [x] Добавить: `sentry-sdk>=1.32`
- [x] Добавить: `Pillow>=10.0` (для изображений)
- [x] Добавить: `django-storages>=1.13` (для S3, опционально)
- [x] Создать `requirements-dev.txt` (pytest, black, flake8, mypy, isort)

**Задача 0.3.4:** Настроить базовую структуру приложений
- [x] Создать приложение `users`: `python manage.py startapp users apps/users`
- [x] Создать приложение `products`: `python manage.py startapp products apps/products`
- [x] Создать приложение `orders`: `python manage.py startapp orders apps/orders`
- [x] Создать приложение `stores`: `python manage.py startapp stores apps/stores`
- [x] Создать приложение `content`: `python manage.py startapp content apps/content`
- [x] Создать приложение `cart`: `python manage.py startapp cart apps/cart`
- [x] Создать приложение `bonus`: `python manage.py startapp bonus apps/bonus`
- [x] Зарегистрировать все приложения в `INSTALLED_APPS`

### 📊 0.4 База данных и миграции

**Задача 0.4.1:** Настроить PostgreSQL
- [x] Создать базу данных в docker-compose
- [x] Настроить переменные окружения для подключения
- [x] Протестировать подключение
- [x] Настроить резервное копирование (опционально для dev)
- [x] Настроить connection pooling (pgbouncer, опционально)

**Задача 0.4.2:** Настроить Redis
- [x] Настроить Redis в docker-compose
- [x] Настроить Celery broker URL
- [x] Настроить кэш backend (Redis)
- [x] Настроить session backend (Redis)
- [x] Протестировать подключение

**Задача 0.4.3:** Настроить Celery
- [x] Создать `config/celery.py`
- [x] Настроить Celery app
- [x] Настроить broker и backend
- [x] Настроить timezone
- [x] Протестировать запуск worker

### 🔐 0.5 Безопасность и мониторинг

**Задача 0.5.1:** Настроить Sentry
- [x] Зарегистрироваться на Sentry (или настроить self-hosted)
- [x] Установить `sentry-sdk`
- [x] Настроить DSN в settings
- [x] Настроить фильтрацию чувствительных данных
- [x] Протестировать отправку ошибок

**Задача 0.5.2:** Настроить секреты
- [x] Создать `.env` файл (не коммитить!)
- [x] Добавить все секреты в `.env.example` (без значений)
- [x] Настроить GitHub Secrets (для CI/CD)
- [x] Настроить переменные окружения в docker-compose
- [x] Использовать `python-dotenv` для загрузки

**Задача 0.5.3:** Настроить базовую безопасность
- [x] Настроить `SECURE_SSL_REDIRECT` (для production)
- [x] Настроить `SESSION_COOKIE_SECURE`
- [x] Настроить `CSRF_COOKIE_SECURE`
- [x] Настроить `SECURE_BROWSER_XSS_FILTER`
- [x] Настроить `SECURE_CONTENT_TYPE_NOSNIFF`
- [x] Добавить security headers middleware
- [x] Настроить `X_FRAME_OPTIONS`

### 📚 0.6 Документация и инструменты разработки

**Задача 0.6.1:** Настроить OpenAPI/Swagger
- [x] Установить `drf-spectacular`
- [x] Настроить в `INSTALLED_APPS`
- [x] Настроить в `REST_FRAMEWORK`
- [x] Добавить URL для Swagger UI
- [x] Добавить URL для ReDoc
- [x] Протестировать генерацию схемы

**Задача 0.6.2:** Создать базовую документацию
- [x] Обновить `README.md` с инструкциями по запуску
- [x] Создать `docs/API.md` (будет заполняться)
- [x] Создать `docs/DEPLOYMENT.md`
- [x] Создать `docs/ARCHITECTURE.md`
- [x] Создать `CONTRIBUTING.md`

**Задача 0.6.3:** Настроить pre-commit hooks
- [x] Установить `pre-commit`
- [x] Создать `.pre-commit-config.yaml`
- [x] Настроить black, flake8, isort, mypy
- [x] Настроить проверку секретов (detect-secrets)
- [x] Настроить проверку для фронтенда (ESLint, Prettier)
- [x] Протестировать hooks

---

## ЭТАП 1: BACKEND - SPRINT A

### 👤 1.1 Модель User и аутентификация

**Задача 1.1.1:** Создать модель CustomUser
- [x] Создать `users/models.py` с `AbstractUser`
- [x] Добавить поле `id` (UUID, primary key)
- [x] Добавить поле `phone` (CharField, unique, indexed)
- [x] Добавить поле `email` (EmailField, unique, nullable)
- [x] Добавить поле `is_phone_verified` (BooleanField, default=False)
- [x] Добавить поле `is_email_verified` (BooleanField, default=False)
- [x] Настроить `USERNAME_FIELD = 'phone'`
- [x] Настроить `REQUIRED_FIELDS = ['email']`
- [x] Добавить `created_at`, `updated_at` (DateTimeField)
- [x] Добавить метод `__str__`
- [x] Создать миграцию: `makemigrations users`
- [x] Применить миграцию: `migrate`

**Задача 1.1.2:** Создать модель UserProfile
- [x] Создать модель `UserProfile`:
  - `user` (OneToOneField to CustomUser)
  - `first_name` (CharField, nullable)
  - `last_name` (CharField, nullable)
  - `middle_name` (CharField, nullable)
  - `avatar` (ImageField, nullable)
  - `birth_date` (DateField, nullable)
  - `gender` (CharField, choices, nullable)
- [x] Добавить метод `__str__`
- [x] Создать миграцию
- [x] Применить миграцию

**Задача 1.1.3:** Создать модель DeliveryAddress
- [x] Создать модель `DeliveryAddress`:
  - `user` (ForeignKey to CustomUser)
  - `title` (CharField, например "Дом", "Работа")
  - `city` (CharField)
  - `street` (CharField)
  - `house` (CharField)
  - `apartment` (CharField, nullable)
  - `postal_code` (CharField, nullable)
  - `is_default` (BooleanField, default=False)
  - `latitude` (DecimalField, nullable, для карт)
  - `longitude` (DecimalField, nullable, для карт)
  - `created_at`, `updated_at`
- [x] Добавить `Meta` класс (ordering, indexes)
- [x] Создать миграцию
- [x] Применить миграцию

**Задача 1.1.4:** Настроить JWT аутентификацию
- [x] Установить `djangorestframework-simplejwt`
- [x] Настроить в `REST_FRAMEWORK` settings
- [x] Настроить `SIMPLE_JWT` settings (access/refresh token lifetime)
- [x] Создать `users/serializers.py` с `UserSerializer`, `UserProfileSerializer`
- [x] Создать `users/views.py` с `UserMeView` (GET /api/v1/auth/me/)
- [x] Создать `users/urls.py` с маршрутами
- [x] Подключить в `config/api_urls.py`

**Задача 1.1.5:** Реализовать SMS аутентификацию - запрос кода
- [x] Создать `users/services.py` для SMS логики
- [x] Создать функцию `generate_sms_code()` (6 цифр)
- [x] Создать функцию `store_sms_code(phone, code)` (Redis, TTL 5 мин)
- [x] Создать функцию `verify_sms_code(phone, code)` (проверка)
- [x] Создать функцию `send_sms(phone, code)` (stub, потом интеграция с sms.ru/Twilio)
- [x] Создать `SMSRequestCodeView` (POST /api/v1/auth/sms/request_code/)
- [x] Добавить валидацию телефона (regex, нормализация)
- [x] Добавить rate limiting (1 запрос в минуту на телефон)
- [x] Добавить обработку ошибок
- [x] Написать unit тесты

**Задача 1.1.6:** Реализовать SMS аутентификацию - верификация
- [x] Создать `SMSVerifyView` (POST /api/v1/auth/sms/verify/)
- [x] Валидировать phone и code
- [x] Проверить код в Redis
- [x] Создать или получить User по телефону
- [x] Сгенерировать JWT токены (access + refresh)
- [x] Вернуть токены в ответе
- [x] Удалить код из Redis после успешной верификации
- [x] Добавить обработку ошибок (неверный код, истекший код)
- [x] Написать unit тесты

**Задача 1.1.7:** Реализовать refresh token endpoint
- [x] Использовать встроенный `TokenRefreshView` из SimpleJWT
- [x] Подключить в `users/urls.py`
- [x] Протестировать обновление токенов

**Задача 1.1.8:** Настроить Admin для User
- [x] Создать `users/admin.py`
- [x] Зарегистрировать `CustomUserAdmin`
- [x] Зарегистрировать `UserProfileAdmin` (inline)
- [x] Зарегистрировать `DeliveryAddressAdmin` (inline)
- [x] Настроить `list_display`, `search_fields`, `list_filter`
- [x] Протестировать в Django Admin

### 📦 1.2 Модели каталога (Category, Product, ProductImage, ProductSpec)

**Задача 1.2.1:** Создать модель Category
- [x] Создать `products/models.py`
- [x] Добавить модель `Category`:
  - `id` (UUID, PK)
  - `title` (CharField, max_length=255)
  - `slug` (SlugField, unique=True)
  - `parent` (ForeignKey to self, nullable)
  - `description` (TextField, nullable)
  - `image` (ImageField, nullable)
  - `sort_order` (IntegerField, default=0)
  - `is_active` (BooleanField, default=True)
  - `meta_title` (CharField, nullable, для SEO)
  - `meta_description` (TextField, nullable, для SEO)
  - `created_at`, `updated_at` (DateTimeField)
- [x] Добавить метод `__str__`
- [x] Добавить метод `get_absolute_url()`
- [x] Добавить `Meta` класс (ordering, verbose_name, indexes)
- [x] Создать миграцию
- [ ] Применить миграцию (`make migrate` или `docker-compose exec web python manage.py migrate`)

**Задача 1.2.2:** Создать модель Product
- [x] Добавить модель `Product`:
  - `id` (UUID, PK)
  - `title` (CharField, max_length=255)
  - `slug` (SlugField, unique)
  - `sku` (CharField, unique, nullable)
  - `description` (TextField, может быть HTML)
  - `short_description` (TextField, nullable)
  - `price` (DecimalField, max_digits=12, decimal_places=2)
  - `old_price` (DecimalField, nullable)
  - `category` (ForeignKey to Category)
  - `brand` (CharField, nullable)
  - `rating` (FloatField, default=0.0)
  - `reviews_count` (IntegerField, default=0)
  - `is_active` (BooleanField, default=True)
  - `is_featured` (BooleanField, default=False)
  - `meta_title` (CharField, nullable)
  - `meta_description` (TextField, nullable)
  - `created_at`, `updated_at`
- [x] Добавить метод `__str__`
- [x] Добавить метод `get_absolute_url()`
- [x] Добавить computed property `discount_percent`
- [x] Добавить `Meta` класс (ordering, indexes)
- [x] Создать миграцию
- [ ] Применить миграцию (входит в общую миграцию каталога)

**Задача 1.2.3:** Создать модель ProductImage
- [x] Добавить модель `ProductImage`:
  - `id` (UUID, PK)
  - `product` (ForeignKey to Product, CASCADE)
  - `image` (ImageField или CharField для S3 URL)
  - `is_main` (BooleanField, default=False)
  - `alt_text` (CharField, nullable)
  - `sort_order` (IntegerField, default=0)
  - `created_at`
- [x] Добавить метод `__str__`
- [x] Добавить `Meta` класс (ordering, unique_together для is_main)
- [x] Добавить сигнал для проверки единственного `is_main=True`
- [x] Создать миграцию
- [ ] Применить миграцию (входит в общую миграцию каталога)

**Задача 1.2.4:** Создать модель ProductSpec (характеристики)
- [x] Добавить модель `ProductSpec`:
  - `id` (UUID, PK)
  - `product` (ForeignKey to Product, CASCADE)
  - `name` (CharField, название характеристики)
  - `value` (CharField, значение)
  - `sort_order` (IntegerField, default=0)
- [x] Добавить метод `__str__`
- [x] Добавить `Meta` класс (ordering)
- [x] Создать миграцию
- [ ] Применить миграцию (входит в общую миграцию каталога)

**Задача 1.2.5:** Создать сериализаторы для каталога
- [x] Создать `products/serializers.py`
- [x] Создать `CategorySerializer` (id, title, slug, parent, image, description)
- [x] Создать `ProductImageSerializer` (id, image, is_main, alt_text)
- [x] Создать `ProductSpecSerializer` (name, value)
- [x] Создать `ProductListSerializer`:
  - Включить `images` (nested, только главное изображение)
  - Включить `category` (nested или id)
  - Добавить computed fields (discount_percent)
- [x] Создать `ProductDetailSerializer` (расширенный):
  - Включить все `images` (nested)
  - Включить все `specs` (nested)
  - Включить `category` (nested)
  - Добавить computed fields
- [x] Написать unit тесты для сериализаторов

**Задача 1.2.6:** Создать ViewSet для Category
- [x] Создать `products/views.py`
- [x] Создать `CategoryViewSet` (ListAPIView, RetrieveAPIView)
- [x] Настроить фильтрацию по `is_active`
- [x] Настроить пагинацию
- [x] Подключить в `products/urls.py`
- [x] Написать unit тесты

**Задача 1.2.7:** Создать ViewSet для Product
- [x] Создать `ProductListView` (ListAPIView):
  - Фильтрация по категории (slug)
  - Фильтрация по цене (min_price, max_price)
  - Поиск по названию (search)
  - Сортировка (price_asc, price_desc, rating_desc, created_at)
  - Пагинация (cursor-based для бесконечного скролла)
- [x] Создать `ProductDetailView` (RetrieveAPIView):
  - Включить все изображения
  - Включить все характеристики
  - Включить наличие в магазинах (через Stock)
  - Включить `is_in_user_cart` (bool, если авторизован)
- [x] Оптимизировать запросы (select_related, prefetch_related)
- [x] Подключить в `products/urls.py`
- [x] Написать unit тесты

**Задача 1.2.8:** Настроить Admin для каталога
- [x] Создать `products/admin.py`
- [x] Зарегистрировать `CategoryAdmin` (list_display, search_fields, list_filter)
- [x] Зарегистрировать `ProductAdmin` (list_display, inlines для images и specs)
- [x] Зарегистрировать `ProductImageAdmin`
- [x] Зарегистрировать `ProductSpecAdmin`
- [x] Настроить inline для ProductImage в ProductAdmin
- [x] Настроить inline для ProductSpec в ProductAdmin
- [x] Протестировать в Django Admin

### 🏪 1.3 Модели магазинов и наличия (Store, Stock)

**Задача 1.3.1:** Создать модель Store
- [x] Создать `stores/models.py`
- [x] Добавить модель `Store`:
  - `id` (UUID, PK)
  - `name` (CharField)
  - `slug` (SlugField, unique)
  - `address` (CharField)
  - `city` (CharField)
  - `phone` (CharField, nullable)
  - `email` (EmailField, nullable)
  - `latitude` (DecimalField, для карт)
  - `longitude` (DecimalField, для карт)
  - `working_hours` (JSONField, например {"monday": "9:00-21:00"})
  - `is_active` (BooleanField, default=True)
  - `created_at`, `updated_at`
- [x] Добавить метод `__str__`
- [x] Добавить метод `get_absolute_url()`
- [x] Добавить `Meta` класс (ordering, indexes)
- [x] Создать миграцию
- [ ] Применить миграцию (make migrate или docker-compose exec web python manage.py migrate)

**Задача 1.3.2:** Создать модель Stock (наличие товара в магазине)
- [x] Добавить модель `Stock`:
  - `id` (UUID, PK)
  - `product` (ForeignKey to Product, CASCADE)
  - `store` (ForeignKey to Store, CASCADE)
  - `quantity` (PositiveIntegerField, default=0)
  - `reserved_quantity` (PositiveIntegerField, default=0, для резервирования)
  - `available_quantity` (property: quantity - reserved_quantity)
  - `updated_at` (DateTimeField, auto_now=True)
- [x] Добавить `Meta` класс (unique_together: product, store, indexes)
- [x] Добавить метод `__str__`
- [x] Добавить метод `reserve(amount)` для резервирования
- [x] Добавить метод `release(amount)` для освобождения резерва
- [x] Создать миграцию
- [ ] Применить миграцию (входит в общую миграцию)

**Задача 1.3.3:** Создать сериализаторы для магазинов
- [x] Создать `stores/serializers.py`
- [x] Создать `StoreSerializer` (id, name, slug, address, city, phone, coordinates, working_hours)
- [x] Создать `StockSerializer` (product, store, quantity, available_quantity)
- [x] Написать unit тесты

**Задача 1.3.4:** Создать API для магазинов
- [x] Создать `stores/views.py`
- [x] Создать `StoreListView` (GET /api/v1/stores/):
  - Фильтрация по `is_active`
  - Фильтрация по `city`
  - Возврат координат для карты
- [x] Создать `StoreDetailView` (GET /api/v1/stores/{id}/):
  - Детали магазина
  - Список товаров в наличии (опционально)
- [x] Создать `StockListView` (GET /api/v1/stores/{id}/stock/):
  - Остатки товаров в конкретном магазине
- [x] Создать `ProductStockView` (GET /api/v1/products/{id}/stock/):
  - Наличие товара во всех магазинах
- [x] Подключить в `stores/urls.py`
- [x] Написать unit тесты

**Задача 1.3.5:** Настроить Admin для магазинов
- [x] Создать `stores/admin.py`
- [x] Зарегистрировать `StoreAdmin` (list_display, search_fields, list_filter)
- [x] Зарегистрировать `StockAdmin` (list_display, list_filter, search_fields)
- [x] Настроить inline для Stock в StoreAdmin
- [x] Протестировать в Django Admin

### 🛒 1.4 Корзина (Cart, CartItem)

**Задача 1.4.1:** Создать модель Cart
- [x] Создать `cart/models.py`
- [x] Добавить модель `Cart`:
  - `id` (UUID, PK)
  - `user` (ForeignKey to CustomUser, nullable)
  - `session_key` (CharField, nullable, для гостей)
  - `created_at`, `updated_at`
- [x] Добавить метод `get_or_create_cart(request)` (classmethod)
- [x] Добавить метод `get_total()` (сумма всех items)
- [x] Добавить метод `__str__`
- [x] Создать миграцию
- [ ] Применить миграцию (make migrate или docker-compose exec web python manage.py migrate)

**Задача 1.4.2:** Создать модель CartItem
- [x] Добавить модель `CartItem`:
  - `id` (UUID, PK)
  - `cart` (ForeignKey to Cart, CASCADE)
  - `product` (ForeignKey to Product, CASCADE)
  - `quantity` (PositiveIntegerField)
  - `price_at_add` (DecimalField, цена на момент добавления)
  - `store` (ForeignKey to Store, nullable, для самовывоза)
  - `created_at`, `updated_at`
- [x] Добавить `Meta` класс (unique_together: cart, product, store)
- [x] Добавить метод `__str__`
- [x] Добавить метод `get_total()` (quantity * price_at_add)
- [x] Создать миграцию
- [ ] Применить миграцию (входит в общую миграцию)

**Задача 1.4.3:** Создать сериализаторы для корзины
- [x] Создать `cart/serializers.py`
- [x] Создать `CartItemSerializer`:
  - Включить `product` (nested ProductListSerializer)
  - Включить `store` (nested StoreSerializer, nullable)
  - Включить computed field `item_total`
- [x] Создать `CartSerializer`:
  - Включить `items` (nested CartItemSerializer, many=True)
  - Включить computed field `total_amount`
- [x] Создать `CartItemCreateSerializer` (для добавления товара)
- [x] Создать `CartItemUpdateSerializer` (для изменения количества)
- [x] Написать unit тесты

**Задача 1.4.4:** Создать API для корзины
- [x] Создать `cart/views.py`
- [x] Создать `CartView` (GET /api/v1/cart/):
  - Получить или создать корзину
  - Вернуть корзину с товарами
- [x] Создать `CartItemCreateView` (POST /api/v1/cart/items/):
  - Валидация product_id, quantity, store_id (опционально)
  - Проверка наличия товара (Stock)
  - Добавить или обновить CartItem
  - Вернуть обновленную корзину
- [x] Создать `CartItemUpdateView` (PATCH /api/v1/cart/items/{id}/):
  - Обновить quantity
  - Проверить наличие товара
  - Удалить если quantity = 0
- [x] Создать `CartItemDeleteView` (DELETE /api/v1/cart/items/{id}/)
- [x] Создать `CartClearView` (POST /api/v1/cart/clear/):
  - Удалить все CartItem
- [x] Подключить в `cart/urls.py`
- [x] Написать unit тесты

**Задача 1.4.5:** Реализовать логику связывания корзины при авторизации
- [x] Создать сигнал `user_logged_in` или middleware
- [x] При авторизации найти корзину по session_key
- [x] Связать корзину с user
- [x] Объединить товары если есть корзина у user
- [x] Написать unit тесты

**Задача 1.4.6:** Настроить Admin для корзины
- [x] Создать `cart/admin.py`
- [x] Зарегистрировать `CartAdmin` (list_display, inlines)
- [x] Зарегистрировать `CartItemAdmin`
- [x] Настроить inline для CartItem в CartAdmin

### 📝 1.5 Заказы (Order, OrderItem)

**Задача 1.5.1:** Создать модель Order
- [x] Создать `orders/models.py`
- [x] Добавить модель `Order`:
  - `id` (UUID, PK)
  - `user` (ForeignKey to CustomUser, nullable)
  - `order_number` (CharField, unique, автогенерация)
  - `full_name` (CharField, required)
  - `phone` (CharField, required)
  - `email` (EmailField, nullable)
  - `delivery_type` (CharField, choices: pickup, delivery)
  - `delivery_address` (JSONField, для доставки: city, street, house, apartment, postal_code)
  - `store` (ForeignKey to Store, nullable, для самовывоза)
  - `payment_type` (CharField, choices: cash, card_on_delivery, bank_transfer, online)
  - `status` (CharField, choices: new, confirmed, in_progress, completed, cancelled)
  - `total_amount` (DecimalField)
  - `delivery_cost` (DecimalField, default=0)
  - `bonus_used` (DecimalField, default=0)
  - `bonus_earned` (DecimalField, default=0)
  - `comment` (TextField, nullable)
  - `created_at`, `updated_at`
- [x] Добавить метод `__str__`
- [x] Добавить `Meta` класс (ordering, indexes)
- [x] Создать миграцию
- [ ] Применить миграцию (make migrate или docker-compose exec web python manage.py migrate)

**Задача 1.5.2:** Создать модель OrderItem
- [x] Добавить модель `OrderItem`:
  - `id` (UUID, PK)
  - `order` (ForeignKey to Order, CASCADE)
  - `product` (ForeignKey to Product, nullable, для истории)
  - `product_title` (CharField, название на момент заказа)
  - `product_sku` (CharField, nullable)
  - `quantity` (PositiveIntegerField)
  - `price` (DecimalField, цена на момент заказа)
  - `item_total` (DecimalField, computed или сохраненное)
- [x] Добавить метод `__str__`
- [x] Добавить `Meta` класс
- [x] Создать миграцию
- [ ] Применить миграцию (входит в общую миграцию)

**Задача 1.5.3:** Создать сериализаторы для заказов
- [x] Создать `orders/serializers.py`
- [x] Создать `OrderItemSerializer` (id, product_title, quantity, price, item_total)
- [x] Создать `OrderSerializer`:
  - Включить `items` (nested OrderItemSerializer)
  - Валидация данных
- [x] Создать `OrderCreateSerializer`:
  - Валидация items (не пустой список)
  - Валидация bonus_used (не больше баланса)
  - Валидация total_amount
  - Валидация delivery_address (если delivery_type = delivery)
- [x] Написать unit тесты

**Задача 1.5.4:** Создать API для заказов - создание
- [x] Создать `orders/views.py`
- [x] Создать `OrderCreateView` (POST /api/v1/orders/):
  - Валидация входных данных
  - Проверка bonus_used <= balance (если user авторизован)
  - Резервирование товаров в Stock (если самовывоз)
  - Создание Order и OrderItem из корзины или из items в запросе
  - Расчет total_amount
  - Расчет delivery_cost (заглушка, потом интеграция)
  - Сохранение заказа
  - Очистка корзины после создания заказа
  - Запуск Celery task для отправки уведомлений (SMS, email)
  - Вернуть созданный заказ
- [x] Обработка ошибок (INSUFFICIENT_BONUS, ORDER_INVALID_ITEMS, INSUFFICIENT_STOCK)
- [x] Подключить в `orders/urls.py`
- [x] Написать unit тесты

**Задача 1.5.5:** Создать API для заказов - просмотр
- [x] Создать `OrderDetailView` (GET /api/v1/orders/{id}/):
  - Проверка прав доступа (только владелец или staff)
  - Вернуть детали заказа
- [x] Создать `OrderListView` (GET /api/v1/orders/):
  - Фильтрация по user (если не staff)
  - Фильтрация по status
  - Пагинация
  - Сортировка по created_at
- [x] Подключить в `orders/urls.py`
- [x] Написать unit тесты

**Задача 1.5.6:** Настроить Admin для заказов
- [x] Создать `orders/admin.py`
- [x] Зарегистрировать `OrderAdmin`:
  - list_display (order_number, full_name, phone, total_amount, status, created_at)
  - list_filter (status, payment_type, delivery_type, created_at)
  - search_fields (phone, full_name, order_number)
  - inlines (OrderItemInline)
  - actions (изменить статус, экспорт CSV)
- [x] Зарегистрировать `OrderItemAdmin`

---

## ЭТАП 2: BACKEND - SPRINT B

### 💎 2.1 Бонусная система

**Задача 2.1.1:** Создать модель BonusAccount
- [x] Создать `bonus/models.py`
- [x] Добавить модель `BonusAccount`:
  - `id` (UUID, PK)
  - `user` (OneToOneField to CustomUser)
  - `balance` (DecimalField, default=0)
  - `total_earned` (DecimalField, default=0)
  - `total_spent` (DecimalField, default=0)
  - `updated_at` (DateTimeField, auto_now=True)
- [x] Добавить метод `__str__`
- [x] Добавить сигнал для автоматического создания при создании User
- [x] Создать миграцию
- [x] Применить миграцию

**Задача 2.1.2:** Создать модель BonusTransaction
- [x] Добавить модель `BonusTransaction`:
  - `id` (UUID, PK)
  - `account` (ForeignKey to BonusAccount)
  - `amount` (DecimalField, может быть отрицательным)
  - `reason` (CharField, choices: order_reward, order_refund, admin_adjust, order_spend)
  - `related_order` (ForeignKey to Order, nullable)
  - `description` (TextField, nullable)
  - `created_at` (DateTimeField, auto_now_add)
- [x] Добавить метод `__str__`
- [x] Добавить `Meta` класс (ordering, indexes)
- [x] Создать миграцию
- [x] Применить миграцию

**Задача 2.1.3:** Создать сервис для работы с бонусами
- [x] Создать `bonus/services.py`
- [x] Создать функцию `add_bonus(account, amount, reason, order=None, description=None)`:
  - Создать BonusTransaction
  - Обновить balance (F() для атомарности)
  - Обновить total_earned
  - Вернуть транзакцию
- [x] Создать функцию `spend_bonus(account, amount, order)`:
  - Проверка что balance >= amount
  - Создать отрицательную транзакцию
  - Обновить balance
  - Обновить total_spent
  - Вернуть транзакцию или None
- [x] Создать функцию `calculate_order_bonus(order)`:
  - Правила начисления (например, 5% от суммы)
  - Вернуть сумму бонусов
- [x] Написать unit тесты

**Задача 2.1.4:** Создать сериализаторы для бонусов
- [x] Создать `bonus/serializers.py`
- [x] Создать `BonusTransactionSerializer` (id, amount, reason, related_order, description, created_at)
- [x] Создать `BonusAccountSerializer`:
  - Включить `transactions` (nested, paginated)
  - Computed fields
- [x] Написать unit тесты

**Задача 2.1.5:** Создать API для бонусов
- [x] Создать `bonus/views.py`
- [x] Создать `BonusAccountView` (GET /api/v1/bonus/):
  - Получить или создать BonusAccount для user
  - Вернуть баланс и транзакции (paginated)
- [x] Создать `BonusTransactionsView` (GET /api/v1/bonus/transactions/):
  - История транзакций с фильтрацией
- [x] Подключить в `bonus/urls.py`
- [x] Написать unit тесты

**Задача 2.1.6:** Интегрировать начисление бонусов при подтверждении заказа
- [x] Создать сигнал или метод в Order model
- [x] При изменении status на 'confirmed'
  - Рассчитать бонусы
  - Начислить на BonusAccount
  - Создать BonusTransaction
- [x] Написать unit тесты

**Задача 2.1.7:** Настроить Admin для бонусов
- [x] Создать `bonus/admin.py`
- [x] Зарегистрировать `BonusAccountAdmin`:
  - list_display (user, balance, total_earned, total_spent, updated_at)
  - search_fields (user__phone)
  - inlines (BonusTransactionInline)
- [x] Зарегистрировать `BonusTransactionAdmin`:
  - list_display (account, amount, reason, created_at)
  - list_filter (reason, created_at)

### 📰 2.2 Контент (Blog, News, Reviews)

**Задача 2.2.1:** Создать модель Article (блог)
- [x] Создать `content/models.py`
- [x] Добавить модель `Article`:
  - `id` (UUID, PK)
  - `title` (CharField)
  - `slug` (SlugField, unique)
  - `content` (TextField, HTML)
  - `excerpt` (TextField, nullable)
  - `image` (ImageField, nullable)
  - `author` (ForeignKey to CustomUser, nullable)
  - `category` (CharField, choices, nullable)
  - `tags` (ManyToManyField to Tag, через промежуточную модель)
  - `is_published` (BooleanField, default=False)
  - `published_at` (DateTimeField, nullable)
  - `views_count` (IntegerField, default=0)
  - `meta_title` (CharField, nullable)
  - `meta_description` (TextField, nullable)
  - `created_at`, `updated_at`
- [x] Добавить метод `__str__`
- [x] Добавить метод `get_absolute_url()`
- [x] Добавить `Meta` класс
- [x] Создать миграцию
- [x] Применить миграцию

**Задача 2.2.2:** Создать модель News
- [x] Добавить модель `News`:
  - Аналогично Article, но упрощенная версия
  - `is_featured` (BooleanField, default=False)
- [x] Создать миграцию
- [x] Применить миграцию

**Задача 2.2.3:** Создать модель Review (отзывы на товары)
- [x] Добавить модель `Review`:
  - `id` (UUID, PK)
  - `product` (ForeignKey to Product, CASCADE)
  - `user` (ForeignKey to CustomUser, nullable)
  - `name` (CharField, если user не авторизован)
  - `email` (EmailField, nullable)
  - `rating` (IntegerField, choices: 1-5)
  - `comment` (TextField)
  - `is_approved` (BooleanField, default=False)
  - `is_verified_purchase` (BooleanField, default=False)
  - `created_at`, `updated_at`
- [x] Добавить `Meta` класс (unique_together: product, user или product, email)
- [x] Добавить сигнал для пересчета рейтинга продукта
- [x] Создать миграцию
- [x] Применить миграцию

**Задача 2.2.4:** Создать модель Tag
- [x] Добавить модель `Tag`:
  - `id` (UUID, PK)
  - `name` (CharField, unique)
  - `slug` (SlugField, unique)
- [x] Создать миграцию
- [x] Применить миграцию

**Задача 2.2.5:** Создать сериализаторы для контента
- [x] Создать `content/serializers.py`
- [x] Создать `ArticleSerializer`, `NewsSerializer`, `ReviewSerializer`, `TagSerializer`
- [x] Написать unit тесты

**Задача 2.2.6:** Создать API для контента
- [x] Создать `content/views.py`
- [x] Создать ViewSets для Article, News, Review
- [x] Настроить фильтрацию, поиск, пагинацию
- [x] Подключить в `content/urls.py`
- [x] Написать unit тесты

**Задача 2.2.7:** Настроить Admin для контента
- [x] Создать `content/admin.py`
- [x] Зарегистрировать все модели
- [x] Настроить list_display, search_fields, list_filter

### 🎁 2.3 Акции и промокоды (Promotion, PromoCode)

**Задача 2.3.1:** Создать модель Promotion
- [x] Создать `promotions/models.py` (новое приложение)
- [x] Добавить модель `Promotion`:
  - `id` (UUID, PK)
  - `title` (CharField)
  - `description` (TextField, nullable)
  - `image` (ImageField, nullable)
  - `discount_type` (CharField, choices: percent, fixed)
  - `discount_value` (DecimalField)
  - `start_date` (DateTimeField)
  - `end_date` (DateTimeField)
  - `is_active` (BooleanField, default=True)
  - `products` (ManyToManyField to Product, через промежуточную модель)
  - `categories` (ManyToManyField to Category, через промежуточную модель)
  - `created_at`, `updated_at`
- [x] Добавить метод `is_valid()` (проверка дат)
- [x] Создать миграцию
- [x] Применить миграцию

**Задача 2.3.2:** Создать модель PromoCode
- [x] Добавить модель `PromoCode`:
  - `id` (UUID, PK)
  - `code` (CharField, unique, uppercase)
  - `discount_type` (CharField, choices)
  - `discount_value` (DecimalField)
  - `max_uses` (IntegerField, nullable)
  - `used_count` (IntegerField, default=0)
  - `min_order_amount` (DecimalField, nullable)
  - `start_date` (DateTimeField)
  - `end_date` (DateTimeField)
  - `is_active` (BooleanField, default=True)
- [x] Добавить метод `is_valid()` (проверка дат, использований)
- [x] Создать миграцию
- [x] Применить миграцию

**Задача 2.3.3:** Создать сервис для применения промокодов
- [x] Создать `promotions/services.py`
- [x] Создать функцию `apply_promo_code(code, order_amount)`:
  - Валидация кода
  - Проверка дат
  - Проверка использований
  - Проверка min_order_amount
  - Расчет скидки
  - Вернуть сумму скидки
- [x] Написать unit тесты

**Задача 2.3.4:** Создать API для промокодов
- [x] Создать `promotions/views.py`
- [x] Создать `PromoCodeValidateView` (POST /api/v1/promocodes/validate/):
  - Валидация промокода
  - Возврат суммы скидки
- [x] Подключить в `promotions/urls.py`
- [x] Написать unit тесты

### 📧 2.4 Интеграции (SMS, Email, Maps)

**Задача 2.4.1:** Интеграция с SMS сервисом
- [x] Создать `integrations/sms_service.py`
- [x] Реализовать отправку SMS через sms.ru или Twilio
- [x] Обработка ошибок
- [x] Логирование отправок
- [x] Написать unit тесты (mock)

**Задача 2.4.2:** Интеграция с Email сервисом
- [x] Настроить Django email backend (SMTP или SendGrid)
- [x] Создать email templates
- [x] Создать функции для отправки:
  - Подтверждение заказа
  - Изменение статуса заказа
  - Оценка менеджера
- [x] Написать unit тесты

**Задача 2.4.3:** Интеграция с картами (Yandex Maps API)
- [x] Создать `integrations/maps_service.py`
- [x] Реализовать геокодирование адресов
- [x] Реализовать расчет расстояния между точками
- [x] Реализовать поиск ближайших магазинов
- [x] Обработка ошибок API
- [x] Написать unit тесты (mock)

**Задача 2.4.4:** Интеграция с CRM (заявки на отсутствующий товар)
- [x] Создать модель `MissingProductRequest`:
  - `id` (UUID, PK)
  - `user` (ForeignKey, nullable)
  - `product_name` (CharField)
  - `contact_phone` (CharField)
  - `contact_email` (EmailField, nullable)
  - `comment` (TextField, nullable)
  - `status` (CharField, choices: new, processed, closed)
  - `created_at`
- [x] Создать API endpoint для создания заявки
- [x] Создать Celery task для отправки в CRM (заглушка)
- [x] Написать unit тесты

### ⚡ 2.5 Кэширование и оптимизация


**Задача 2.5.1:** Настроить Redis кэш
- [x] Настроить `CACHES` в settings (Redis backend)
- [x] Установить `django-redis`
- [x] Настроить cache timeout для разных типов данных
- [x] Протестировать подключение

**Задача 2.5.2:** Реализовать кэширование списка товаров
- [x] В `ProductListView`:
  - Кэшировать queryset на 5 минут
  - Инвалидировать при изменении Product/Category
- [x] Использовать cache key с учетом фильтров
- [x] Написать unit тесты

**Задача 2.5.3:** Реализовать кэширование категорий
- [x] В `CategoryListView`:
  - Кэшировать дерево категорий на 10 минут
- [x] Инвалидировать при изменении Category
- [x] Написать unit тесты

**Задача 2.5.4:** Оптимизировать запросы (select_related, prefetch_related)
- [x] В ProductListView: prefetch_related('images', 'category')
- [x] В ProductDetailView: select_related('category'), prefetch_related('images', 'specs', 'stock_set')
- [x] В OrderDetailView: prefetch_related('items')
- [x] Использовать `django-debug-toolbar` для анализа (dev only)

### 🚦 2.6 Rate Limiting и безопасность

**Задача 2.6.1:** Настроить rate limiting для SMS endpoints
- [x] Установить `django-ratelimit` или использовать DRF throttling
- [x] Настроить для `SMSRequestCodeView`:
  - 1 запрос в минуту на IP
  - 3 запроса в час на телефон
- [x] Настроить для `SMSVerifyView`:
  - 5 попыток в 10 минут на телефон
- [x] Вернуть правильные HTTP статусы (429)
- [x] Написать unit тесты

**Задача 2.6.2:** Настроить общий throttling для API
- [x] Настроить в `REST_FRAMEWORK` settings:
  - `DEFAULT_THROTTLE_CLASSES`
  - `DEFAULT_THROTTLE_RATES` (anon, user)
- [x] Настроить для разных endpoints разные лимиты
- [x] Протестировать

**Задача 2.6.3:** Улучшить безопасность
- [x] Настроить CORS правильно (только нужные домены)
- [x] Добавить валидацию входных данных везде
- [x] Настроить CSRF protection для нужных endpoints
- [x] Добавить проверку прав доступа везде
- [x] Провести security audit (опционально, использовать bandit)

---

## ЭТАП 3: FRONTEND - SPRINT C

### 📱 3.1 Инициализация Next.js проекта

**Задача 3.1.1:** Создать Next.js проект
- [x] Создать проект: `npx create-next-app@latest frontend --typescript --tailwind --app`
- [x] Настроить `package.json`: название, версия, описание
- [x] Проверить что проект запускается

**Задача 3.1.2:** Настроить зависимости
- [x] Добавить в `package.json`:
  - `@tanstack/react-query` (state management)
  - `axios` или `fetch` (HTTP клиент)
  - `framer-motion` (анимации)
  - `zustand` (клиентское состояние)
  - `react-hook-form` (формы)
  - `zod` (валидация)
  - `date-fns` (работа с датами)
  - `swiper` (галереи изображений)
  - `react-intersection-observer` (lazy loading)
- [x] Выполнить `npm install`

**Задача 3.1.3:** Настроить структуру проекта
- [x] Создать структуру папок:
  ```
  app/
  components/
    ui/
    layout/
    features/
  lib/
    api/
    utils/
    hooks/
  types/
  public/
  ```
- [x] Создать базовые файлы в каждой папке

**Задача 3.1.4:** Настроить TypeScript
- [x] Настроить `tsconfig.json`
- [x] Создать типы для API responses
- [x] Настроить path aliases (@/components, @/lib)

**Задача 3.1.5:** Настроить Tailwind CSS
- [x] Настроить `tailwind.config.js`
- [x] Определить цветовую схему (brand colors)
- [x] Определить типографику
- [x] Создать кастомные компоненты (Button, Input, Card)

### 🔌 3.2 API клиент и сетевой слой

**Задача 3.2.1:** Создать базовый API клиент
- [x] Создать `lib/api/client.ts`
- [x] Настроить axios с base URL
- [x] Настроить interceptors:
  - Request interceptor (добавление токенов)
  - Response interceptor (обработка ошибок)
  - Error interceptor (retry логика, refresh token)
- [x] Настроить timeout
- [x] Протестировать базовое подключение

**Задача 3.2.2:** Создать типы данных (TypeScript interfaces)
- [x] Создать `types/api.ts`
- [x] Создать интерфейсы:
  - `User`, `Product`, `Category`, `Cart`, `Order`, `Store`, `Stock`
  - `ApiResponse`, `PaginatedResponse`
- [x] Экспортировать все типы

**Задача 3.2.3:** Создать API сервисы
- [x] Создать `lib/api/services/` папку
- [x] Создать `auth.service.ts`:
  - `requestSmsCode(phone)`
  - `verifySmsCode(phone, code)`
  - `refreshToken(refreshToken)`
  - `getMe()`
- [x] Создать `products.service.ts`:
  - `getCategories()`
  - `getProducts(filters)`
  - `getProductDetail(id)`
- [x] Создать `cart.service.ts`:
  - `getCart()`
  - `addToCart(productId, quantity, storeId?)`
  - `updateCartItem(itemId, quantity)`
  - `removeCartItem(itemId)`
  - `clearCart()`
- [x] Создать `orders.service.ts`:
  - `createOrder(orderData)`
  - `getOrder(id)`
  - `getOrders(filters)`
- [x] Создать `stores.service.ts`:
  - `getStores(filters)`
  - `getStoreDetail(id)`
  - `getProductStock(productId)`
- [x] Создать `bonus.service.ts`:
  - `getBonusAccount()`
  - `getBonusTransactions()`

**Задача 3.2.4:** Настроить React Query
- [x] Создать `lib/providers/QueryProvider.tsx`
- [x] Настроить `QueryClient` с default options
- [x] Настроить error handling
- [x] Подключить в `app/layout.tsx`

**Задача 3.2.5:** Настроить управление токенами
- [x] Создать `lib/storage/token-storage.ts`
- [x] Сохранение access и refresh токенов (localStorage или cookies)
- [x] Автоматическое обновление токенов при истечении
- [x] Очистка токенов при logout
- [x] Протестировать

### 🎨 3.3 UI компоненты и дизайн-система

**Задача 3.3.1:** Создать базовые UI компоненты
- [x] Создать `components/ui/Button.tsx`:
  - Варианты (primary, secondary, outline, ghost)
  - Размеры (sm, md, lg)
  - Состояния (loading, disabled)
  - Hover анимации
- [x] Создать `components/ui/Input.tsx`:
  - Варианты (text, email, phone, password)
  - Состояния (error, disabled)
  - Иконки (prefix, suffix)
- [x] Создать `components/ui/Card.tsx`:
  - Варианты использования
  - Hover эффекты
- [x] Создать `components/ui/Modal.tsx`:
  - Анимация появления/исчезновения
  - Закрытие по клику вне модалки
- [x] Создать `components/ui/Loading.tsx`:
  - Spinner компонент
  - Skeleton loaders

**Задача 3.3.2:** Создать layout компоненты
- [x] Создать `components/layout/Header.tsx`:
  - Логотип
  - Навигация
  - Корзина (с badge количеством)
  - Профиль пользователя
- [x] Создать `components/layout/Footer.tsx`:
  - Ссылки
  - Контакты
  - Социальные сети
- [x] Создать `components/layout/MobileMenu.tsx`:
  - Off-canvas меню для мобильных
  - Анимация открытия/закрытия

**Задача 3.3.3:** Настроить тему и стили
- [x] Создать `lib/theme/colors.ts` (цветовая палитра)
- [x] Создать `lib/theme/typography.ts` (шрифты, размеры)
- [x] Настроить dark mode (опционально)
- [x] Создать utility функции для стилей

### 📦 3.4 Каталог товаров

**Задача 3.4.1:** Создать страницу каталога
- [x] Создать `app/catalog/page.tsx`
- [x] Реализовать grid товаров
- [x] Реализовать бесконечный скролл (useInfiniteQuery)
- [x] Реализовать фильтры в off-canvas панели на мобильных
- [x] Реализовать чипсы выбранных фильтров
- [x] Реализовать сортировку
- [x] Реализовать поиск
- [x] Оптимизировать производительность (lazy loading изображений)
- [ ] Протестировать

**Задача 3.4.2:** Создать компонент ProductCard
- [x] Создать `components/features/products/ProductCard.tsx`
- [x] Отображение изображения (lazy loading)
- [x] Отображение названия, цены
- [x] Старая цена (зачеркнутая)
- [x] Скидка (бейдж)
- [x] Рейтинг (звезды)
- [x] Кнопка "В корзину"
- [x] Hover эффекты
- [x] Анимация при добавлении в корзину (Framer Motion)
- [ ] Протестировать

**Задача 3.4.3:** Создать страницу карточки товара (PDP)
- [x] Создать `app/products/[slug]/page.tsx`
- [x] Реализовать галерею изображений (Swiper):
  - [x] Главное изображение
  - [x] Превью миниатюр
  - [x] Zoom на главном изображении
- [x] Реализовать таблицу характеристик (адаптивная)
- [x] Реализовать выбор магазина для самовывоза:
  - [x] Интеграция с картой (Yandex Maps)
  - [x] Отображение наличия в магазинах
  - [x] Выбор магазина
- [x] Реализовать кнопки "В корзину", "Купить в 1 клик"
- [x] Реализовать модальное окно "Купить в 1 клик"
- [x] Реализовать секцию отзывов
- [ ] Оптимизировать производительность
- [x] Протестировать

**Задача 3.4.4:** Создать React Query hooks для каталога
- [x] Создать `lib/hooks/useProducts.ts`:
  - [x] `useProducts(filters)` - список товаров
  - [x] `useProduct(slug)` - детали товара
  - [x] `useCategories()` - категории
- [x] Кэширование данных
- [ ] Инвалидация при обновлении
- [x] Протестировать

### 🛒 3.5 Корзина

**Задача 3.5.1:** Создать страницу корзины
- [x] Создать `app/cart/page.tsx`
- [x] Список товаров в корзине
- [x] Изменение количества (+/-)
- [x] Удаление товара
- [x] Показ цены за товар и общей суммы
- [x] Применение промокода (поле ввода)
- [x] Применение бонусов (слайдер или поле ввода)
- [x] Итоговая сумма
- [x] Кнопка "Оформить заказ"
- [x] Пустая корзина (placeholder с анимацией)
- [x] Протестировать

**Задача 3.5.2:** Создать компонент CartItem
- [x] Создать `components/features/cart/CartItem.tsx`
- [x] Изображение товара
- [x] Название, цена
- [x] Счетчик количества
- [x] Кнопка удаления
- [x] Анимация при удалении
- [x] Протестировать

**Задача 3.5.3:** Создать React Query hooks для корзины
- [x] Создать `lib/hooks/useCart.ts`:
  - [x] `useCart()` - получение корзины
  - [x] `useAddToCart()` - добавление в корзину
  - [x] `useUpdateCartItem()` - обновление количества
  - [x] `useRemoveCartItem()` - удаление товара
  - [x] `useClearCart()` - очистка корзины
- [x] Оптимистичные обновления
- [x] Обработка ошибок
- [x] Протестировать

### ✅ 3.6 Оформление заказа

**Задача 3.6.1:** Создать страницу оформления заказа
- [x] Создать `app/checkout/page.tsx`
- [x] Многошаговая форма (stepper):
  - [x] Шаг 1: Корзина (краткий обзор)
  - [x] Шаг 2: Доставка (тип доставки, адрес)
  - [x] Шаг 3: Оплата (способ оплаты)
  - [x] Шаг 4: Подтверждение
- [x] Форма доставки:
  - [x] Тип доставки (Radio: самовывоз/доставка)
  - [x] Выбор магазина (если самовывоз, интеграция с картой)
  - [x] Адрес доставки (если доставка, интеграция с картой для автозаполнения — пока заглушка)
  - [x] Комментарий
- [x] Форма оплаты:
  - [x] Тип оплаты (Radio: наличные/карта при получении/перевод/онлайн)
- [x] Применение промокода
- [x] Применение бонусов
- [x] Расчет итоговой суммы
- [x] Валидация всех полей
- [x] Обработка ошибок
- [x] Протестировать

**Задача 3.6.2:** Создать страницу подтверждения заказа
- [x] Создать `app/orders/[id]/success/page.tsx`
- [x] Номер заказа
- [x] Статус заказа
- [x] Информация о заказе
- [x] Кнопка "Перейти к заказам"
- [x] Кнопка "Вернуться в каталог"
- [x] Протестировать

**Задача 3.6.3:** Создать React Query hooks для заказов
- [x] Создать `lib/hooks/useOrders.ts`:
  - [x] `useCreateOrder()` - создание заказа
  - [x] `useOrder(id)` - детали заказа
  - [x] `useOrders(filters)` - список заказов
- [x] Обработка ошибок
- [x] Протестировать

### 👤 3.7 Личный кабинет

**Задача 3.7.1:** Создать страницу профиля
- [x] Создать `app/profile/page.tsx`
- [x] Информация о пользователе (ФИО, телефон, email)
- [x] Кнопка "Редактировать профиль"
- [x] Баланс бонусов (с переходом на Bonus Screen)
- [x] История заказов (краткий список с переходом на Order History)
- [x] Адреса доставки (список с возможностью редактирования)
- [x] Настройки (язык, уведомления)
- [x] Кнопка "Выйти"
- [x] Протестировать

**Задача 3.7.2:** Создать страницу истории заказов
- [x] Создать `app/orders/page.tsx`
- [x] Список заказов (с пагинацией)
- [x] Фильтрация по статусу
- [x] Сортировка по дате
- [x] Pull to refresh
- [x] Навигация на детальную страницу заказа
- [x] Протестировать

**Задача 3.7.3:** Создать страницу деталей заказа
- [x] Создать `app/orders/[id]/page.tsx`
- [x] Полная информация о заказе
- [x] Список товаров
- [x] Статус заказа (с индикатором прогресса)
- [x] Информация о доставке
- [x] Информация об оплате
- [x] Кнопка "Связаться с поддержкой" (опционально)
- [x] Протестировать

**Задача 3.7.4:** Создать страницу бонусов
- [x] Создать `app/bonus/page.tsx`
- [x] Текущий баланс бонусов (крупно)
- [x] История транзакций (список)
- [x] Фильтрация по типу транзакции
- [x] Пагинация
- [x] Протестировать

### 🗺️ 3.8 Интеграция с картами

**Задача 3.8.1:** Настроить Yandex Maps API
- [x] Установить `@pbe/react-yandex-maps` или использовать нативный API
- [x] Создать компонент `components/features/maps/YandexMap.tsx`
- [x] Настроить API ключ
- [x] Реализовать отображение карты
- [x] Реализовать маркеры магазинов
- [x] Реализовать выбор магазина по клику на маркер
- [x] Протестировать

**Задача 3.8.2:** Реализовать выбор магазина для самовывоза
- [x] Создать компонент `components/features/stores/StoreSelector.tsx`
- [x] Интеграция с картой
- [x] Отображение списка магазинов
- [x] Фильтрация по расстоянию
- [x] Выбор магазина
- [x] Протестировать

**Задача 3.8.3:** Реализовать автозаполнение адреса доставки
- [x] Создать компонент `components/features/maps/AddressAutocomplete.tsx`
- [x] Интеграция с Yandex Maps Geocoder API
- [x] Автозаполнение адреса при вводе
- [x] Получение координат
- [x] Протестировать

### 📰 3.9 Блог и новости

**Задача 3.9.1:** Создать страницу блога
- [x] Создать `app/blog/page.tsx`
- [x] Список статей (grid)
- [x] Фильтрация по категориям
- [x] Фильтрация по тегам
- [x] Поиск
- [x] Пагинация
- [x] SSG для SEO (generateStaticParams)
- [x] Протестировать

**Задача 3.9.2:** Создать страницу статьи
- [ ] Создать `app/blog/[slug]/page.tsx`
- [ ] Полный контент статьи
- [ ] Изображение
- [ ] Автор, дата публикации
- [ ] Теги
- [ ] Похожие статьи
- [ ] SSG для SEO
- [ ] Протестировать

**Задача 3.9.3:** Создать страницу новостей
- [ ] Создать `app/news/page.tsx`
- [ ] Список новостей
- [ ] Фильтрация по дате
- [ ] SSG для SEO
- [ ] Протестировать

### 🎁 3.10 Акции и промокоды

**Задача 3.10.1:** Создать страницу акций
- [x] Создать `app/promotions/page.tsx`
- [x] Список активных акций
- [x] Таймер до конца акции
- [x] Фильтрация по категориям
- [x] Протестировать

**Задача 3.10.2:** Реализовать применение промокода
- [ ] Создать компонент `components/features/promotions/PromoCodeInput.tsx`
- [ ] Поле ввода промокода
- [ ] Валидация промокода
- [ ] Отображение скидки
- [ ] Применение к заказу
- [ ] Протестировать

### 🎨 3.11 Микроанимации и производительность

**Задача 3.11.1:** Реализовать микроанимации на главной странице
- [x] Создать `app/page.tsx` (главная)
- [x] Hero-блок с параллаксом (Framer Motion)
- [x] Анимация появления элементов при скролле
- [x] Плавные переходы
- [x] Оптимизировать для 60 FPS
- [ ] Протестировать на мобильных устройствах

**Задача 3.11.2:** Реализовать плавные переходы между страницами
- [x] Настроить `next-view-transitions` или использовать Framer Motion
- [x] Анимация переходов
- [x] Оптимизировать производительность
- [ ] Протестировать

**Задача 3.11.3:** Оптимизировать производительность
- [x] Lazy loading изображений (next/image)
- [x] Code splitting (динамические импорты)
- [x] Оптимизация шрифтов (next/font)
- [x] Минификация CSS и JS
- [ ] Провести Lighthouse аудит
- [ ] Исправить проблемы (цель: >85 Performance)
- [ ] Протестировать

### 🧪 3.12 Тестирование фронтенда

**Задача 3.12.1:** Настроить тестовое окружение
- [x] Установить `@testing-library/react`, `@testing-library/jest-dom`
- [x] Настроить Vitest (вместо Jest; уже в проекте)
- [x] Создать test helpers (`src/test/helpers.tsx` — renderWithProviders)
- [x] Настроить mock для API (`src/test/mocks/api.ts` — mockCart, mockProduct и др.)

**Задача 3.12.2:** Написать unit тесты
- [x] Тесты для компонентов (критичные: Button, Input, Card, CartItem; страницы уже тестируются)
- [x] Тесты для hooks (useProducts, useProduct, useCategories, useIsClient; useCart/useOrders были ранее)
- [x] Тесты для утилит (cn, getMediaUrl, formatDate)
- [x] Coverage: порог 50% по включённым файлам (components, lib/hooks, lib/utils, lib/theme/utils, image-url); цель 70% — достигать по мере добавления тестов

**Задача 3.12.3:** Написать E2E тесты (опционально)
- [ ] Установить Playwright или Cypress
- [ ] Тест полного flow: каталог → корзина → заказ
- [ ] Тест авторизации
- [ ] Протестировать

---

## ЭТАП 4: ИНТЕГРАЦИИ И ПРОДВИНУТЫЕ ФУНКЦИИ

### 🔔 4.1 Уведомления

**Задача 4.1.1:** Реализовать WebSocket уведомления (Django Channels)
- [ ] Установить `channels`, `channels-redis`
- [ ] Настроить ASGI application
- [ ] Создать consumers для уведомлений
- [ ] Реализовать отправку уведомлений при изменении статуса заказа
- [ ] Интегрировать на фронтенде (WebSocket клиент)
- [ ] Протестировать

**Задача 4.1.2:** Реализовать Push уведомления (опционально)
- [ ] Настроить Firebase Cloud Messaging
- [ ] Реализовать отправку push уведомлений
- [ ] Интегрировать на фронтенде
- [ ] Протестировать

### 📊 4.2 Аналитика

**Задача 4.2.1:** Интеграция с Google Analytics / Yandex Metrica
- [ ] Настроить Google Analytics 4
- [ ] Настроить Yandex Metrica
- [ ] Реализовать отслеживание событий:
  - Просмотр товара
  - Добавление в корзину
  - Оформление заказа
- [ ] Протестировать

### 🔍 4.3 Поиск

**Задача 4.3.1:** Реализовать полнотекстовый поиск
- [ ] Настроить PostgreSQL full-text search или Elasticsearch
- [ ] Реализовать поиск по товарам
- [ ] Реализовать автодополнение
- [ ] Оптимизировать производительность
- [ ] Протестировать

### 📱 4.4 Адаптивность и PWA

**Задача 4.4.1:** Оптимизировать для мобильных устройств
- [ ] Mobile-first подход
- [ ] Тестирование на разных устройствах
- [ ] Исправление проблем с touch событиями
- [ ] Оптимизация производительности на мобильных

**Задача 4.4.2:** Реализовать PWA (Progressive Web App)
- [ ] Создать `manifest.json`
- [ ] Настроить service worker
- [ ] Реализовать офлайн режим (кэширование)
- [ ] Добавить иконки для разных устройств
- [ ] Протестировать

---

## ЭТАП 5: QA, ТЕСТИРОВАНИЕ И РЕЛИЗ

### 🧪 5.1 Комплексное тестирование

**Задача 5.1.1:** Составить тест-план
- [ ] Создать документ с тест-кейсами
- [ ] Покрыть все основные сценарии
- [ ] Приоритизировать тест-кейсы

**Задача 5.1.2:** Провести функциональное тестирование
- [ ] Тестирование всех API endpoints
- [ ] Тестирование всех страниц фронтенда
- [ ] Тестирование интеграций
- [ ] Тестирование edge cases
- [ ] Задокументировать найденные баги
- [ ] Исправить критичные баги

**Задача 5.1.3:** Провести тестирование производительности
- [ ] Нагрузочное тестирование API (Locust/JMeter)
- [ ] Тестирование времени отклика
- [ ] Lighthouse аудит (цель: >85 Performance)
- [ ] Оптимизация найденных проблем

**Задача 5.1.4:** Провести тестирование безопасности
- [ ] Проверка на OWASP Top 10
- [ ] Тестирование аутентификации и авторизации
- [ ] Тестирование защиты данных
- [ ] Тестирование rate limiting
- [ ] Исправить найденные уязвимости

### 🚀 5.2 Деплой и релиз

**Задача 5.2.1:** Настроить production окружение
- [ ] Создать production сервер (VPS)
- [ ] Настроить базу данных (production)
- [ ] Настроить Redis (production)
- [ ] Настроить Nginx
- [ ] Настроить SSL сертификаты (Let's Encrypt)
- [ ] Настроить мониторинг (Sentry, health checks)

**Задача 5.2.2:** Настроить CI/CD для production
- [ ] Настроить автоматический деплой на staging
- [ ] Настроить ручной деплой на production (с approval)
- [ ] Настроить rollback механизм
- [ ] Настроить health checks
- [ ] Протестировать деплой процесс

**Задача 5.2.3:** Настроить резервное копирование
- [ ] Настроить ежедневные бэкапы БД
- [ ] Настроить бэкапы медиа файлов
- [ ] Протестировать восстановление из бэкапа
- [ ] Документировать процесс восстановления

**Задача 5.2.4:** Финальная проверка перед релизом
- [ ] Проверить работу всех функций
- [ ] Проверить производительность
- [ ] Проверить безопасность
- [ ] Проверить адаптивность
- [ ] Получить approval от заказчика

---

## 📊 ИТОГОВАЯ СТАТИСТИКА ПЛАНА

### Общее количество задач:
- **ЭТАП 0:** ~30 задач
- **ЭТАП 1:** ~60 задач
- **ЭТАП 2:** ~50 задач
- **ЭТАП 3:** ~80 задач
- **ЭТАП 4:** ~15 задач
- **ЭТАП 5:** ~15 задач

**Всего: ~250 атомарных задач**

### Ориентировочные сроки:
- **ЭТАП 0:** 3-5 дней
- **ЭТАП 1:** 10-14 дней
- **ЭТАП 2:** 10-14 дней
- **ЭТАП 3:** 14-20 дней
- **ЭТАП 4:** 5-7 дней
- **ЭТАП 5:** 7-10 дней

**Всего: 49-70 рабочих дней (~10-14 недель)**

---

## 📝 ПРИМЕЧАНИЯ

1. **Параллельная разработка:** Backend и Frontend можно разрабатывать параллельно после завершения ЭТАП 0 и базовых API в ЭТАП 1.

2. **Итеративность:** План можно выполнять итеративно, выпуская MVP после каждого этапа.

3. **Гибкость:** Задачи можно переставлять и приоритизировать в зависимости от требований.

4. **Тестирование:** Тесты следует писать параллельно с разработкой, а не в конце.

5. **Документация:** Документацию следует обновлять по мере разработки.

6. **Производительность:** Цель Lighthouse Performance >85 должна проверяться на каждом этапе фронтенда.

---

**Удачи в разработке! 🚀**
