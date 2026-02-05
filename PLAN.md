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
- **Next.js 15 (App Router)** - SSR/SSG для SEO и производительности
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
- [ ] Создать `.github/workflows/backend-ci.yml`
- [ ] Создать `.github/workflows/frontend-ci.yml`
- [ ] Настроить линтеры для Python (black, isort, flake8, mypy)
- [ ] Настроить линтеры для TypeScript (ESLint, Prettier)
- [ ] Добавить проверку на PR (lint + tests)
- [ ] Настроить автоматический запуск тестов

### 🐳 0.2 Docker и локальная среда разработки

**Задача 0.2.1:** Создать Dockerfile для backend
- [ ] Создать `backend/Dockerfile` (multi-stage build)
- [ ] Настроить Python 3.11-slim базовый образ
- [ ] Оптимизировать слои кэширования (requirements.txt отдельно)
- [ ] Добавить healthcheck
- [ ] Настроить non-root user для безопасности
- [ ] Настроить рабочий каталог

**Задача 0.2.2:** Создать docker-compose для разработки
- [ ] Создать `docker-compose.yml` в корне
- [ ] Настроить сервис `web` (Django)
- [ ] Настроить сервис `db` (PostgreSQL 15)
- [ ] Настроить сервис `redis` (Redis 7)
- [ ] Настроить сервис `celery` (worker)
- [ ] Настроить сервис `celery-beat` (scheduler, опционально)
- [ ] Настроить volumes для данных и кода
- [ ] Настроить networks для изоляции
- [ ] Настроить environment variables

**Задача 0.2.3:** Создать файлы окружения
- [ ] Создать `backend/.env.example` с всеми переменными
- [ ] Создать `backend/.env.development`
- [ ] Создать `backend/.env.production` (шаблон)
- [ ] Создать `frontend/.env.example`
- [ ] Создать `frontend/.env.local` (для разработки)
- [ ] Добавить инструкции по настройке в README

**Задача 0.2.4:** Настроить Makefile для удобства
- [ ] Создать `Makefile` с командами:
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
- [ ] Создать виртуальное окружение (или использовать Docker)
- [ ] Установить Django 5.0+ и зависимости
- [ ] Создать проект: `django-admin startproject config backend/`
- [ ] Настроить базовую структуру приложений в `backend/apps/`
- [ ] Создать структуру: `apps/users/`, `apps/products/`, `apps/orders/`, `apps/stores/`, `apps/content/`, `apps/cart/`, `apps/bonus/`

**Задача 0.3.2:** Настроить settings.py
- [ ] Разделить на `base.py`, `development.py`, `production.py`, `test.py`
- [ ] Настроить `SECRET_KEY` из переменных окружения
- [ ] Настроить `DEBUG`, `ALLOWED_HOSTS`
- [ ] Настроить `DATABASES` (PostgreSQL)
- [ ] Настроить `AUTH_USER_MODEL = 'users.CustomUser'`
- [ ] Настроить `INSTALLED_APPS` (базовые + наши)
- [ ] Настроить `MIDDLEWARE`
- [ ] Настроить `STATIC_URL`, `MEDIA_URL`, `STATIC_ROOT`, `MEDIA_ROOT`
- [ ] Настроить `TIME_ZONE`, `LANGUAGE_CODE`
- [ ] Добавить `CORS` настройки для фронтенда
- [ ] Настроить `REST_FRAMEWORK` settings

**Задача 0.3.3:** Настроить базовые зависимости
- [ ] Создать `backend/requirements.txt`
- [ ] Добавить: `Django>=5.0,<6.0`
- [ ] Добавить: `djangorestframework>=3.14`
- [ ] Добавить: `djangorestframework-simplejwt>=5.2`
- [ ] Добавить: `psycopg2-binary>=2.9`
- [ ] Добавить: `celery[redis]>=5.3`
- [ ] Добавить: `redis>=5.0`
- [ ] Добавить: `python-dotenv>=1.0`
- [ ] Добавить: `drf-spectacular>=0.26` (OpenAPI)
- [ ] Добавить: `django-cors-headers>=4.2`
- [ ] Добавить: `sentry-sdk>=1.32`
- [ ] Добавить: `Pillow>=10.0` (для изображений)
- [ ] Добавить: `django-storages>=1.13` (для S3, опционально)
- [ ] Создать `requirements-dev.txt` (pytest, black, flake8, mypy, isort)

**Задача 0.3.4:** Настроить базовую структуру приложений
- [ ] Создать приложение `users`: `python manage.py startapp users apps/users`
- [ ] Создать приложение `products`: `python manage.py startapp products apps/products`
- [ ] Создать приложение `orders`: `python manage.py startapp orders apps/orders`
- [ ] Создать приложение `stores`: `python manage.py startapp stores apps/stores`
- [ ] Создать приложение `content`: `python manage.py startapp content apps/content`
- [ ] Создать приложение `cart`: `python manage.py startapp cart apps/cart`
- [ ] Создать приложение `bonus`: `python manage.py startapp bonus apps/bonus`
- [ ] Зарегистрировать все приложения в `INSTALLED_APPS`

### 📊 0.4 База данных и миграции

**Задача 0.4.1:** Настроить PostgreSQL
- [ ] Создать базу данных в docker-compose
- [ ] Настроить переменные окружения для подключения
- [ ] Протестировать подключение
- [ ] Настроить резервное копирование (опционально для dev)
- [ ] Настроить connection pooling (pgbouncer, опционально)

**Задача 0.4.2:** Настроить Redis
- [ ] Настроить Redis в docker-compose
- [ ] Настроить Celery broker URL
- [ ] Настроить кэш backend (Redis)
- [ ] Настроить session backend (Redis)
- [ ] Протестировать подключение

**Задача 0.4.3:** Настроить Celery
- [ ] Создать `config/celery.py`
- [ ] Настроить Celery app
- [ ] Настроить broker и backend
- [ ] Настроить timezone
- [ ] Протестировать запуск worker

### 🔐 0.5 Безопасность и мониторинг

**Задача 0.5.1:** Настроить Sentry
- [ ] Зарегистрироваться на Sentry (или настроить self-hosted)
- [ ] Установить `sentry-sdk`
- [ ] Настроить DSN в settings
- [ ] Настроить фильтрацию чувствительных данных
- [ ] Протестировать отправку ошибок

**Задача 0.5.2:** Настроить секреты
- [ ] Создать `.env` файл (не коммитить!)
- [ ] Добавить все секреты в `.env.example` (без значений)
- [ ] Настроить GitHub Secrets (для CI/CD)
- [ ] Настроить переменные окружения в docker-compose
- [ ] Использовать `python-dotenv` для загрузки

**Задача 0.5.3:** Настроить базовую безопасность
- [ ] Настроить `SECURE_SSL_REDIRECT` (для production)
- [ ] Настроить `SESSION_COOKIE_SECURE`
- [ ] Настроить `CSRF_COOKIE_SECURE`
- [ ] Настроить `SECURE_BROWSER_XSS_FILTER`
- [ ] Настроить `SECURE_CONTENT_TYPE_NOSNIFF`
- [ ] Добавить security headers middleware
- [ ] Настроить `X_FRAME_OPTIONS`

### 📚 0.6 Документация и инструменты разработки

**Задача 0.6.1:** Настроить OpenAPI/Swagger
- [ ] Установить `drf-spectacular`
- [ ] Настроить в `INSTALLED_APPS`
- [ ] Настроить в `REST_FRAMEWORK`
- [ ] Добавить URL для Swagger UI
- [ ] Добавить URL для ReDoc
- [ ] Протестировать генерацию схемы

**Задача 0.6.2:** Создать базовую документацию
- [ ] Обновить `README.md` с инструкциями по запуску
- [ ] Создать `docs/API.md` (будет заполняться)
- [ ] Создать `docs/DEPLOYMENT.md`
- [ ] Создать `docs/ARCHITECTURE.md`
- [ ] Создать `CONTRIBUTING.md`

**Задача 0.6.3:** Настроить pre-commit hooks
- [ ] Установить `pre-commit`
- [ ] Создать `.pre-commit-config.yaml`
- [ ] Настроить black, flake8, isort, mypy
- [ ] Настроить проверку секретов (detect-secrets)
- [ ] Настроить проверку для фронтенда (ESLint, Prettier)
- [ ] Протестировать hooks

---

## ЭТАП 1: BACKEND - SPRINT A

### 👤 1.1 Модель User и аутентификация

**Задача 1.1.1:** Создать модель CustomUser
- [ ] Создать `users/models.py` с `AbstractUser`
- [ ] Добавить поле `id` (UUID, primary key)
- [ ] Добавить поле `phone` (CharField, unique, indexed)
- [ ] Добавить поле `email` (EmailField, unique, nullable)
- [ ] Добавить поле `is_phone_verified` (BooleanField, default=False)
- [ ] Добавить поле `is_email_verified` (BooleanField, default=False)
- [ ] Настроить `USERNAME_FIELD = 'phone'`
- [ ] Настроить `REQUIRED_FIELDS = ['email']`
- [ ] Добавить `created_at`, `updated_at` (DateTimeField)
- [ ] Добавить метод `__str__`
- [ ] Создать миграцию: `makemigrations users`
- [ ] Применить миграцию: `migrate`

**Задача 1.1.2:** Создать модель UserProfile
- [ ] Создать модель `UserProfile`:
  - `user` (OneToOneField to CustomUser)
  - `first_name` (CharField, nullable)
  - `last_name` (CharField, nullable)
  - `middle_name` (CharField, nullable)
  - `avatar` (ImageField, nullable)
  - `birth_date` (DateField, nullable)
  - `gender` (CharField, choices, nullable)
- [ ] Добавить метод `__str__`
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 1.1.3:** Создать модель DeliveryAddress
- [ ] Создать модель `DeliveryAddress`:
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
- [ ] Добавить `Meta` класс (ordering, indexes)
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 1.1.4:** Настроить JWT аутентификацию
- [ ] Установить `djangorestframework-simplejwt`
- [ ] Настроить в `REST_FRAMEWORK` settings
- [ ] Настроить `SIMPLE_JWT` settings (access/refresh token lifetime)
- [ ] Создать `users/serializers.py` с `UserSerializer`, `UserProfileSerializer`
- [ ] Создать `users/views.py` с `UserMeView` (GET /api/v1/auth/me/)
- [ ] Создать `users/urls.py` с маршрутами
- [ ] Подключить в `config/api_urls.py`

**Задача 1.1.5:** Реализовать SMS аутентификацию - запрос кода
- [ ] Создать `users/services.py` для SMS логики
- [ ] Создать функцию `generate_sms_code()` (6 цифр)
- [ ] Создать функцию `store_sms_code(phone, code)` (Redis, TTL 5 мин)
- [ ] Создать функцию `verify_sms_code(phone, code)` (проверка)
- [ ] Создать функцию `send_sms(phone, code)` (stub, потом интеграция с sms.ru/Twilio)
- [ ] Создать `SMSRequestCodeView` (POST /api/v1/auth/sms/request_code/)
- [ ] Добавить валидацию телефона (regex, нормализация)
- [ ] Добавить rate limiting (1 запрос в минуту на телефон)
- [ ] Добавить обработку ошибок
- [ ] Написать unit тесты

**Задача 1.1.6:** Реализовать SMS аутентификацию - верификация
- [ ] Создать `SMSVerifyView` (POST /api/v1/auth/sms/verify/)
- [ ] Валидировать phone и code
- [ ] Проверить код в Redis
- [ ] Создать или получить User по телефону
- [ ] Сгенерировать JWT токены (access + refresh)
- [ ] Вернуть токены в ответе
- [ ] Удалить код из Redis после успешной верификации
- [ ] Добавить обработку ошибок (неверный код, истекший код)
- [ ] Написать unit тесты

**Задача 1.1.7:** Реализовать refresh token endpoint
- [ ] Использовать встроенный `TokenRefreshView` из SimpleJWT
- [ ] Подключить в `users/urls.py`
- [ ] Протестировать обновление токенов

**Задача 1.1.8:** Настроить Admin для User
- [ ] Создать `users/admin.py`
- [ ] Зарегистрировать `CustomUserAdmin`
- [ ] Зарегистрировать `UserProfileAdmin` (inline)
- [ ] Зарегистрировать `DeliveryAddressAdmin` (inline)
- [ ] Настроить `list_display`, `search_fields`, `list_filter`
- [ ] Протестировать в Django Admin

### 📦 1.2 Модели каталога (Category, Product, ProductImage, ProductSpec)

**Задача 1.2.1:** Создать модель Category
- [ ] Создать `products/models.py`
- [ ] Добавить модель `Category`:
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
- [ ] Добавить метод `__str__`
- [ ] Добавить метод `get_absolute_url()`
- [ ] Добавить `Meta` класс (ordering, verbose_name, indexes)
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 1.2.2:** Создать модель Product
- [ ] Добавить модель `Product`:
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
- [ ] Добавить метод `__str__`
- [ ] Добавить метод `get_absolute_url()`
- [ ] Добавить computed property `discount_percent`
- [ ] Добавить `Meta` класс (ordering, indexes)
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 1.2.3:** Создать модель ProductImage
- [ ] Добавить модель `ProductImage`:
  - `id` (UUID, PK)
  - `product` (ForeignKey to Product, CASCADE)
  - `image` (ImageField или CharField для S3 URL)
  - `is_main` (BooleanField, default=False)
  - `alt_text` (CharField, nullable)
  - `sort_order` (IntegerField, default=0)
  - `created_at`
- [ ] Добавить метод `__str__`
- [ ] Добавить `Meta` класс (ordering, unique_together для is_main)
- [ ] Добавить сигнал для проверки единственного `is_main=True`
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 1.2.4:** Создать модель ProductSpec (характеристики)
- [ ] Добавить модель `ProductSpec`:
  - `id` (UUID, PK)
  - `product` (ForeignKey to Product, CASCADE)
  - `name` (CharField, название характеристики)
  - `value` (CharField, значение)
  - `sort_order` (IntegerField, default=0)
- [ ] Добавить метод `__str__`
- [ ] Добавить `Meta` класс (ordering)
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 1.2.5:** Создать сериализаторы для каталога
- [ ] Создать `products/serializers.py`
- [ ] Создать `CategorySerializer` (id, title, slug, parent, image, description)
- [ ] Создать `ProductImageSerializer` (id, image, is_main, alt_text)
- [ ] Создать `ProductSpecSerializer` (name, value)
- [ ] Создать `ProductListSerializer`:
  - Включить `images` (nested, только главное изображение)
  - Включить `category` (nested или id)
  - Добавить computed fields (discount_percent)
- [ ] Создать `ProductDetailSerializer` (расширенный):
  - Включить все `images` (nested)
  - Включить все `specs` (nested)
  - Включить `category` (nested)
  - Добавить computed fields
- [ ] Написать unit тесты для сериализаторов

**Задача 1.2.6:** Создать ViewSet для Category
- [ ] Создать `products/views.py`
- [ ] Создать `CategoryViewSet` (ListAPIView, RetrieveAPIView)
- [ ] Настроить фильтрацию по `is_active`
- [ ] Настроить пагинацию
- [ ] Подключить в `products/urls.py`
- [ ] Написать unit тесты

**Задача 1.2.7:** Создать ViewSet для Product
- [ ] Создать `ProductListView` (ListAPIView):
  - Фильтрация по категории (slug)
  - Фильтрация по цене (min_price, max_price)
  - Поиск по названию (search)
  - Сортировка (price_asc, price_desc, rating_desc, created_at)
  - Пагинация (cursor-based для бесконечного скролла)
- [ ] Создать `ProductDetailView` (RetrieveAPIView):
  - Включить все изображения
  - Включить все характеристики
  - Включить наличие в магазинах (через Stock)
  - Включить `is_in_user_cart` (bool, если авторизован)
- [ ] Оптимизировать запросы (select_related, prefetch_related)
- [ ] Подключить в `products/urls.py`
- [ ] Написать unit тесты

**Задача 1.2.8:** Настроить Admin для каталога
- [ ] Создать `products/admin.py`
- [ ] Зарегистрировать `CategoryAdmin` (list_display, search_fields, list_filter)
- [ ] Зарегистрировать `ProductAdmin` (list_display, inlines для images и specs)
- [ ] Зарегистрировать `ProductImageAdmin`
- [ ] Зарегистрировать `ProductSpecAdmin`
- [ ] Настроить inline для ProductImage в ProductAdmin
- [ ] Настроить inline для ProductSpec в ProductAdmin
- [ ] Протестировать в Django Admin

### 🏪 1.3 Модели магазинов и наличия (Store, Stock)

**Задача 1.3.1:** Создать модель Store
- [ ] Создать `stores/models.py`
- [ ] Добавить модель `Store`:
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
- [ ] Добавить метод `__str__`
- [ ] Добавить метод `get_absolute_url()`
- [ ] Добавить `Meta` класс (ordering, indexes)
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 1.3.2:** Создать модель Stock (наличие товара в магазине)
- [ ] Добавить модель `Stock`:
  - `id` (UUID, PK)
  - `product` (ForeignKey to Product, CASCADE)
  - `store` (ForeignKey to Store, CASCADE)
  - `quantity` (PositiveIntegerField, default=0)
  - `reserved_quantity` (PositiveIntegerField, default=0, для резервирования)
  - `available_quantity` (property: quantity - reserved_quantity)
  - `updated_at` (DateTimeField, auto_now=True)
- [ ] Добавить `Meta` класс (unique_together: product, store, indexes)
- [ ] Добавить метод `__str__`
- [ ] Добавить метод `reserve(amount)` для резервирования
- [ ] Добавить метод `release(amount)` для освобождения резерва
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 1.3.3:** Создать сериализаторы для магазинов
- [ ] Создать `stores/serializers.py`
- [ ] Создать `StoreSerializer` (id, name, slug, address, city, phone, coordinates, working_hours)
- [ ] Создать `StockSerializer` (product, store, quantity, available_quantity)
- [ ] Написать unit тесты

**Задача 1.3.4:** Создать API для магазинов
- [ ] Создать `stores/views.py`
- [ ] Создать `StoreListView` (GET /api/v1/stores/):
  - Фильтрация по `is_active`
  - Фильтрация по `city`
  - Возврат координат для карты
- [ ] Создать `StoreDetailView` (GET /api/v1/stores/{id}/):
  - Детали магазина
  - Список товаров в наличии (опционально)
- [ ] Создать `StockListView` (GET /api/v1/stores/{id}/stock/):
  - Остатки товаров в конкретном магазине
- [ ] Создать `ProductStockView` (GET /api/v1/products/{id}/stock/):
  - Наличие товара во всех магазинах
- [ ] Подключить в `stores/urls.py`
- [ ] Написать unit тесты

**Задача 1.3.5:** Настроить Admin для магазинов
- [ ] Создать `stores/admin.py`
- [ ] Зарегистрировать `StoreAdmin` (list_display, search_fields, list_filter)
- [ ] Зарегистрировать `StockAdmin` (list_display, list_filter, search_fields)
- [ ] Настроить inline для Stock в StoreAdmin
- [ ] Протестировать в Django Admin

### 🛒 1.4 Корзина (Cart, CartItem)

**Задача 1.4.1:** Создать модель Cart
- [ ] Создать `cart/models.py`
- [ ] Добавить модель `Cart`:
  - `id` (UUID, PK)
  - `user` (ForeignKey to CustomUser, nullable)
  - `session_key` (CharField, nullable, для гостей)
  - `created_at`, `updated_at`
- [ ] Добавить метод `get_or_create_cart(request)` (classmethod)
- [ ] Добавить метод `get_total()` (сумма всех items)
- [ ] Добавить метод `__str__`
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 1.4.2:** Создать модель CartItem
- [ ] Добавить модель `CartItem`:
  - `id` (UUID, PK)
  - `cart` (ForeignKey to Cart, CASCADE)
  - `product` (ForeignKey to Product, CASCADE)
  - `quantity` (PositiveIntegerField)
  - `price_at_add` (DecimalField, цена на момент добавления)
  - `store` (ForeignKey to Store, nullable, для самовывоза)
  - `created_at`, `updated_at`
- [ ] Добавить `Meta` класс (unique_together: cart, product, store)
- [ ] Добавить метод `__str__`
- [ ] Добавить метод `get_total()` (quantity * price_at_add)
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 1.4.3:** Создать сериализаторы для корзины
- [ ] Создать `cart/serializers.py`
- [ ] Создать `CartItemSerializer`:
  - Включить `product` (nested ProductListSerializer)
  - Включить `store` (nested StoreSerializer, nullable)
  - Включить computed field `item_total`
- [ ] Создать `CartSerializer`:
  - Включить `items` (nested CartItemSerializer, many=True)
  - Включить computed field `total_amount`
- [ ] Создать `CartItemCreateSerializer` (для добавления товара)
- [ ] Создать `CartItemUpdateSerializer` (для изменения количества)
- [ ] Написать unit тесты

**Задача 1.4.4:** Создать API для корзины
- [ ] Создать `cart/views.py`
- [ ] Создать `CartView` (GET /api/v1/cart/):
  - Получить или создать корзину
  - Вернуть корзину с товарами
- [ ] Создать `CartItemCreateView` (POST /api/v1/cart/items/):
  - Валидация product_id, quantity, store_id (опционально)
  - Проверка наличия товара (Stock)
  - Добавить или обновить CartItem
  - Вернуть обновленную корзину
- [ ] Создать `CartItemUpdateView` (PATCH /api/v1/cart/items/{id}/):
  - Обновить quantity
  - Проверить наличие товара
  - Удалить если quantity = 0
- [ ] Создать `CartItemDeleteView` (DELETE /api/v1/cart/items/{id}/)
- [ ] Создать `CartClearView` (POST /api/v1/cart/clear/):
  - Удалить все CartItem
- [ ] Подключить в `cart/urls.py`
- [ ] Написать unit тесты

**Задача 1.4.5:** Реализовать логику связывания корзины при авторизации
- [ ] Создать сигнал `user_logged_in` или middleware
- [ ] При авторизации найти корзину по session_key
- [ ] Связать корзину с user
- [ ] Объединить товары если есть корзина у user
- [ ] Написать unit тесты

**Задача 1.4.6:** Настроить Admin для корзины
- [ ] Создать `cart/admin.py`
- [ ] Зарегистрировать `CartAdmin` (list_display, inlines)
- [ ] Зарегистрировать `CartItemAdmin`
- [ ] Настроить inline для CartItem в CartAdmin

### 📝 1.5 Заказы (Order, OrderItem)

**Задача 1.5.1:** Создать модель Order
- [ ] Создать `orders/models.py`
- [ ] Добавить модель `Order`:
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
- [ ] Добавить метод `__str__`
- [ ] Добавить `Meta` класс (ordering, indexes)
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 1.5.2:** Создать модель OrderItem
- [ ] Добавить модель `OrderItem`:
  - `id` (UUID, PK)
  - `order` (ForeignKey to Order, CASCADE)
  - `product` (ForeignKey to Product, nullable, для истории)
  - `product_title` (CharField, название на момент заказа)
  - `product_sku` (CharField, nullable)
  - `quantity` (PositiveIntegerField)
  - `price` (DecimalField, цена на момент заказа)
  - `item_total` (DecimalField, computed или сохраненное)
- [ ] Добавить метод `__str__`
- [ ] Добавить `Meta` класс
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 1.5.3:** Создать сериализаторы для заказов
- [ ] Создать `orders/serializers.py`
- [ ] Создать `OrderItemSerializer` (id, product_title, quantity, price, item_total)
- [ ] Создать `OrderSerializer`:
  - Включить `items` (nested OrderItemSerializer)
  - Валидация данных
- [ ] Создать `OrderCreateSerializer`:
  - Валидация items (не пустой список)
  - Валидация bonus_used (не больше баланса)
  - Валидация total_amount
  - Валидация delivery_address (если delivery_type = delivery)
- [ ] Написать unit тесты

**Задача 1.5.4:** Создать API для заказов - создание
- [ ] Создать `orders/views.py`
- [ ] Создать `OrderCreateView` (POST /api/v1/orders/):
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
- [ ] Обработка ошибок (INSUFFICIENT_BONUS, ORDER_INVALID_ITEMS, INSUFFICIENT_STOCK)
- [ ] Подключить в `orders/urls.py`
- [ ] Написать unit тесты

**Задача 1.5.5:** Создать API для заказов - просмотр
- [ ] Создать `OrderDetailView` (GET /api/v1/orders/{id}/):
  - Проверка прав доступа (только владелец или staff)
  - Вернуть детали заказа
- [ ] Создать `OrderListView` (GET /api/v1/orders/):
  - Фильтрация по user (если не staff)
  - Фильтрация по status
  - Пагинация
  - Сортировка по created_at
- [ ] Подключить в `orders/urls.py`
- [ ] Написать unit тесты

**Задача 1.5.6:** Настроить Admin для заказов
- [ ] Создать `orders/admin.py`
- [ ] Зарегистрировать `OrderAdmin`:
  - list_display (order_number, full_name, phone, total_amount, status, created_at)
  - list_filter (status, payment_type, delivery_type, created_at)
  - search_fields (phone, full_name, order_number)
  - inlines (OrderItemInline)
  - actions (изменить статус, экспорт CSV)
- [ ] Зарегистрировать `OrderItemAdmin`

---

## ЭТАП 2: BACKEND - SPRINT B

### 💎 2.1 Бонусная система

**Задача 2.1.1:** Создать модель BonusAccount
- [ ] Создать `bonus/models.py`
- [ ] Добавить модель `BonusAccount`:
  - `id` (UUID, PK)
  - `user` (OneToOneField to CustomUser)
  - `balance` (DecimalField, default=0)
  - `total_earned` (DecimalField, default=0)
  - `total_spent` (DecimalField, default=0)
  - `updated_at` (DateTimeField, auto_now=True)
- [ ] Добавить метод `__str__`
- [ ] Добавить сигнал для автоматического создания при создании User
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 2.1.2:** Создать модель BonusTransaction
- [ ] Добавить модель `BonusTransaction`:
  - `id` (UUID, PK)
  - `account` (ForeignKey to BonusAccount)
  - `amount` (DecimalField, может быть отрицательным)
  - `reason` (CharField, choices: order_reward, order_refund, admin_adjust, order_spend)
  - `related_order` (ForeignKey to Order, nullable)
  - `description` (TextField, nullable)
  - `created_at` (DateTimeField, auto_now_add)
- [ ] Добавить метод `__str__`
- [ ] Добавить `Meta` класс (ordering, indexes)
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 2.1.3:** Создать сервис для работы с бонусами
- [ ] Создать `bonus/services.py`
- [ ] Создать функцию `add_bonus(account, amount, reason, order=None, description=None)`:
  - Создать BonusTransaction
  - Обновить balance (F() для атомарности)
  - Обновить total_earned
  - Вернуть транзакцию
- [ ] Создать функцию `spend_bonus(account, amount, order)`:
  - Проверка что balance >= amount
  - Создать отрицательную транзакцию
  - Обновить balance
  - Обновить total_spent
  - Вернуть транзакцию или None
- [ ] Создать функцию `calculate_order_bonus(order)`:
  - Правила начисления (например, 5% от суммы)
  - Вернуть сумму бонусов
- [ ] Написать unit тесты

**Задача 2.1.4:** Создать сериализаторы для бонусов
- [ ] Создать `bonus/serializers.py`
- [ ] Создать `BonusTransactionSerializer` (id, amount, reason, related_order, description, created_at)
- [ ] Создать `BonusAccountSerializer`:
  - Включить `transactions` (nested, paginated)
  - Computed fields
- [ ] Написать unit тесты

**Задача 2.1.5:** Создать API для бонусов
- [ ] Создать `bonus/views.py`
- [ ] Создать `BonusAccountView` (GET /api/v1/bonus/):
  - Получить или создать BonusAccount для user
  - Вернуть баланс и транзакции (paginated)
- [ ] Создать `BonusTransactionsView` (GET /api/v1/bonus/transactions/):
  - История транзакций с фильтрацией
- [ ] Подключить в `bonus/urls.py`
- [ ] Написать unit тесты

**Задача 2.1.6:** Интегрировать начисление бонусов при подтверждении заказа
- [ ] Создать сигнал или метод в Order model
- [ ] При изменении status на 'confirmed'
  - Рассчитать бонусы
  - Начислить на BonusAccount
  - Создать BonusTransaction
- [ ] Написать unit тесты

**Задача 2.1.7:** Настроить Admin для бонусов
- [ ] Создать `bonus/admin.py`
- [ ] Зарегистрировать `BonusAccountAdmin`:
  - list_display (user, balance, total_earned, total_spent, updated_at)
  - search_fields (user__phone)
  - inlines (BonusTransactionInline)
- [ ] Зарегистрировать `BonusTransactionAdmin`:
  - list_display (account, amount, reason, created_at)
  - list_filter (reason, created_at)

### 📰 2.2 Контент (Blog, News, Reviews)

**Задача 2.2.1:** Создать модель Article (блог)
- [ ] Создать `content/models.py`
- [ ] Добавить модель `Article`:
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
- [ ] Добавить метод `__str__`
- [ ] Добавить метод `get_absolute_url()`
- [ ] Добавить `Meta` класс
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 2.2.2:** Создать модель News
- [ ] Добавить модель `News`:
  - Аналогично Article, но упрощенная версия
  - `is_featured` (BooleanField, default=False)
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 2.2.3:** Создать модель Review (отзывы на товары)
- [ ] Добавить модель `Review`:
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
- [ ] Добавить `Meta` класс (unique_together: product, user или product, email)
- [ ] Добавить сигнал для пересчета рейтинга продукта
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 2.2.4:** Создать модель Tag
- [ ] Добавить модель `Tag`:
  - `id` (UUID, PK)
  - `name` (CharField, unique)
  - `slug` (SlugField, unique)
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 2.2.5:** Создать сериализаторы для контента
- [ ] Создать `content/serializers.py`
- [ ] Создать `ArticleSerializer`, `NewsSerializer`, `ReviewSerializer`, `TagSerializer`
- [ ] Написать unit тесты

**Задача 2.2.6:** Создать API для контента
- [ ] Создать `content/views.py`
- [ ] Создать ViewSets для Article, News, Review
- [ ] Настроить фильтрацию, поиск, пагинацию
- [ ] Подключить в `content/urls.py`
- [ ] Написать unit тесты

**Задача 2.2.7:** Настроить Admin для контента
- [ ] Создать `content/admin.py`
- [ ] Зарегистрировать все модели
- [ ] Настроить list_display, search_fields, list_filter

### 🎁 2.3 Акции и промокоды (Promotion, PromoCode)

**Задача 2.3.1:** Создать модель Promotion
- [ ] Создать `promotions/models.py` (новое приложение)
- [ ] Добавить модель `Promotion`:
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
- [ ] Добавить метод `is_valid()` (проверка дат)
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 2.3.2:** Создать модель PromoCode
- [ ] Добавить модель `PromoCode`:
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
- [ ] Добавить метод `is_valid()` (проверка дат, использований)
- [ ] Создать миграцию
- [ ] Применить миграцию

**Задача 2.3.3:** Создать сервис для применения промокодов
- [ ] Создать `promotions/services.py`
- [ ] Создать функцию `apply_promo_code(code, order_amount)`:
  - Валидация кода
  - Проверка дат
  - Проверка использований
  - Проверка min_order_amount
  - Расчет скидки
  - Вернуть сумму скидки
- [ ] Написать unit тесты

**Задача 2.3.4:** Создать API для промокодов
- [ ] Создать `promotions/views.py`
- [ ] Создать `PromoCodeValidateView` (POST /api/v1/promocodes/validate/):
  - Валидация промокода
  - Возврат суммы скидки
- [ ] Подключить в `promotions/urls.py`
- [ ] Написать unit тесты

### 📧 2.4 Интеграции (SMS, Email, Maps)

**Задача 2.4.1:** Интеграция с SMS сервисом
- [ ] Создать `integrations/sms_service.py`
- [ ] Реализовать отправку SMS через sms.ru или Twilio
- [ ] Обработка ошибок
- [ ] Логирование отправок
- [ ] Написать unit тесты (mock)

**Задача 2.4.2:** Интеграция с Email сервисом
- [ ] Настроить Django email backend (SMTP или SendGrid)
- [ ] Создать email templates
- [ ] Создать функции для отправки:
  - Подтверждение заказа
  - Изменение статуса заказа
  - Оценка менеджера
- [ ] Написать unit тесты

**Задача 2.4.3:** Интеграция с картами (Yandex Maps API)
- [ ] Создать `integrations/maps_service.py`
- [ ] Реализовать геокодирование адресов
- [ ] Реализовать расчет расстояния между точками
- [ ] Реализовать поиск ближайших магазинов
- [ ] Обработка ошибок API
- [ ] Написать unit тесты (mock)

**Задача 2.4.4:** Интеграция с CRM (заявки на отсутствующий товар)
- [ ] Создать модель `MissingProductRequest`:
  - `id` (UUID, PK)
  - `user` (ForeignKey, nullable)
  - `product_name` (CharField)
  - `contact_phone` (CharField)
  - `contact_email` (EmailField, nullable)
  - `comment` (TextField, nullable)
  - `status` (CharField, choices: new, processed, closed)
  - `created_at`
- [ ] Создать API endpoint для создания заявки
- [ ] Создать Celery task для отправки в CRM (заглушка)
- [ ] Написать unit тесты

### ⚡ 2.5 Кэширование и оптимизация

**Задача 2.5.1:** Настроить Redis кэш
- [ ] Настроить `CACHES` в settings (Redis backend)
- [ ] Установить `django-redis`
- [ ] Настроить cache timeout для разных типов данных
- [ ] Протестировать подключение

**Задача 2.5.2:** Реализовать кэширование списка товаров
- [ ] В `ProductListView`:
  - Кэшировать queryset на 5 минут
  - Инвалидировать при изменении Product/Category
- [ ] Использовать cache key с учетом фильтров
- [ ] Написать unit тесты

**Задача 2.5.3:** Реализовать кэширование категорий
- [ ] В `CategoryListView`:
  - Кэшировать дерево категорий на 10 минут
- [ ] Инвалидировать при изменении Category
- [ ] Написать unit тесты

**Задача 2.5.4:** Оптимизировать запросы (select_related, prefetch_related)
- [ ] В ProductListView: prefetch_related('images', 'category')
- [ ] В ProductDetailView: select_related('category'), prefetch_related('images', 'specs', 'stock_set')
- [ ] В OrderDetailView: prefetch_related('items')
- [ ] Использовать `django-debug-toolbar` для анализа (dev only)

### 🚦 2.6 Rate Limiting и безопасность

**Задача 2.6.1:** Настроить rate limiting для SMS endpoints
- [ ] Установить `django-ratelimit` или использовать DRF throttling
- [ ] Настроить для `SMSRequestCodeView`:
  - 1 запрос в минуту на IP
  - 3 запроса в час на телефон
- [ ] Настроить для `SMSVerifyView`:
  - 5 попыток в 10 минут на телефон
- [ ] Вернуть правильные HTTP статусы (429)
- [ ] Написать unit тесты

**Задача 2.6.2:** Настроить общий throttling для API
- [ ] Настроить в `REST_FRAMEWORK` settings:
  - `DEFAULT_THROTTLE_CLASSES`
  - `DEFAULT_THROTTLE_RATES` (anon, user)
- [ ] Настроить для разных endpoints разные лимиты
- [ ] Протестировать

**Задача 2.6.3:** Улучшить безопасность
- [ ] Настроить CORS правильно (только нужные домены)
- [ ] Добавить валидацию входных данных везде
- [ ] Настроить CSRF protection для нужных endpoints
- [ ] Добавить проверку прав доступа везде
- [ ] Провести security audit (опционально, использовать bandit)

---

## ЭТАП 3: FRONTEND - SPRINT C

### 📱 3.1 Инициализация Next.js проекта

**Задача 3.1.1:** Создать Next.js проект
- [ ] Создать проект: `npx create-next-app@latest frontend --typescript --tailwind --app`
- [ ] Настроить `package.json`: название, версия, описание
- [ ] Проверить что проект запускается

**Задача 3.1.2:** Настроить зависимости
- [ ] Добавить в `package.json`:
  - `@tanstack/react-query` (state management)
  - `axios` или `fetch` (HTTP клиент)
  - `framer-motion` (анимации)
  - `zustand` (клиентское состояние)
  - `react-hook-form` (формы)
  - `zod` (валидация)
  - `date-fns` (работа с датами)
  - `swiper` (галереи изображений)
  - `react-intersection-observer` (lazy loading)
- [ ] Выполнить `npm install`

**Задача 3.1.3:** Настроить структуру проекта
- [ ] Создать структуру папок:
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
- [ ] Создать базовые файлы в каждой папке

**Задача 3.1.4:** Настроить TypeScript
- [ ] Настроить `tsconfig.json`
- [ ] Создать типы для API responses
- [ ] Настроить path aliases (@/components, @/lib)

**Задача 3.1.5:** Настроить Tailwind CSS
- [ ] Настроить `tailwind.config.js`
- [ ] Определить цветовую схему (brand colors)
- [ ] Определить типографику
- [ ] Создать кастомные компоненты (Button, Input, Card)

### 🔌 3.2 API клиент и сетевой слой

**Задача 3.2.1:** Создать базовый API клиент
- [ ] Создать `lib/api/client.ts`
- [ ] Настроить axios с base URL
- [ ] Настроить interceptors:
  - Request interceptor (добавление токенов)
  - Response interceptor (обработка ошибок)
  - Error interceptor (retry логика, refresh token)
- [ ] Настроить timeout
- [ ] Протестировать базовое подключение

**Задача 3.2.2:** Создать типы данных (TypeScript interfaces)
- [ ] Создать `types/api.ts`
- [ ] Создать интерфейсы:
  - `User`, `Product`, `Category`, `Cart`, `Order`, `Store`, `Stock`
  - `ApiResponse`, `PaginatedResponse`
- [ ] Экспортировать все типы

**Задача 3.2.3:** Создать API сервисы
- [ ] Создать `lib/api/services/` папку
- [ ] Создать `auth.service.ts`:
  - `requestSmsCode(phone)`
  - `verifySmsCode(phone, code)`
  - `refreshToken(refreshToken)`
  - `getMe()`
- [ ] Создать `products.service.ts`:
  - `getCategories()`
  - `getProducts(filters)`
  - `getProductDetail(id)`
- [ ] Создать `cart.service.ts`:
  - `getCart()`
  - `addToCart(productId, quantity, storeId?)`
  - `updateCartItem(itemId, quantity)`
  - `removeCartItem(itemId)`
  - `clearCart()`
- [ ] Создать `orders.service.ts`:
  - `createOrder(orderData)`
  - `getOrder(id)`
  - `getOrders(filters)`
- [ ] Создать `stores.service.ts`:
  - `getStores(filters)`
  - `getStoreDetail(id)`
  - `getProductStock(productId)`
- [ ] Создать `bonus.service.ts`:
  - `getBonusAccount()`
  - `getBonusTransactions()`

**Задача 3.2.4:** Настроить React Query
- [ ] Создать `lib/providers/QueryProvider.tsx`
- [ ] Настроить `QueryClient` с default options
- [ ] Настроить error handling
- [ ] Подключить в `app/layout.tsx`

**Задача 3.2.5:** Настроить управление токенами
- [ ] Создать `lib/storage/token-storage.ts`
- [ ] Сохранение access и refresh токенов (localStorage или cookies)
- [ ] Автоматическое обновление токенов при истечении
- [ ] Очистка токенов при logout
- [ ] Протестировать

### 🎨 3.3 UI компоненты и дизайн-система

**Задача 3.3.1:** Создать базовые UI компоненты
- [ ] Создать `components/ui/Button.tsx`:
  - Варианты (primary, secondary, outline, ghost)
  - Размеры (sm, md, lg)
  - Состояния (loading, disabled)
  - Hover анимации
- [ ] Создать `components/ui/Input.tsx`:
  - Варианты (text, email, phone, password)
  - Состояния (error, disabled)
  - Иконки (prefix, suffix)
- [ ] Создать `components/ui/Card.tsx`:
  - Варианты использования
  - Hover эффекты
- [ ] Создать `components/ui/Modal.tsx`:
  - Анимация появления/исчезновения
  - Закрытие по клику вне модалки
- [ ] Создать `components/ui/Loading.tsx`:
  - Spinner компонент
  - Skeleton loaders

**Задача 3.3.2:** Создать layout компоненты
- [ ] Создать `components/layout/Header.tsx`:
  - Логотип
  - Навигация
  - Корзина (с badge количеством)
  - Профиль пользователя
- [ ] Создать `components/layout/Footer.tsx`:
  - Ссылки
  - Контакты
  - Социальные сети
- [ ] Создать `components/layout/MobileMenu.tsx`:
  - Off-canvas меню для мобильных
  - Анимация открытия/закрытия

**Задача 3.3.3:** Настроить тему и стили
- [ ] Создать `lib/theme/colors.ts` (цветовая палитра)
- [ ] Создать `lib/theme/typography.ts` (шрифты, размеры)
- [ ] Настроить dark mode (опционально)
- [ ] Создать utility функции для стилей

### 📦 3.4 Каталог товаров

**Задача 3.4.1:** Создать страницу каталога
- [ ] Создать `app/catalog/page.tsx`
- [ ] Реализовать grid товаров
- [ ] Реализовать бесконечный скролл (useInfiniteQuery)
- [ ] Реализовать фильтры в off-canvas панели на мобильных
- [ ] Реализовать чипсы выбранных фильтров
- [ ] Реализовать сортировку
- [ ] Реализовать поиск
- [ ] Оптимизировать производительность (lazy loading изображений)
- [ ] Протестировать

**Задача 3.4.2:** Создать компонент ProductCard
- [ ] Создать `components/features/products/ProductCard.tsx`
- [ ] Отображение изображения (lazy loading)
- [ ] Отображение названия, цены
- [ ] Старая цена (зачеркнутая)
- [ ] Скидка (бейдж)
- [ ] Рейтинг (звезды)
- [ ] Кнопка "В корзину"
- [ ] Hover эффекты
- [ ] Анимация при добавлении в корзину (Framer Motion)
- [ ] Протестировать

**Задача 3.4.3:** Создать страницу карточки товара (PDP)
- [ ] Создать `app/products/[slug]/page.tsx`
- [ ] Реализовать галерею изображений (Swiper):
  - Главное изображение
  - Превью миниатюр
  - Zoom на главном изображении
- [ ] Реализовать таблицу характеристик (адаптивная)
- [ ] Реализовать выбор магазина для самовывоза:
  - Интеграция с картой (Yandex Maps)
  - Отображение наличия в магазинах
  - Выбор магазина
- [ ] Реализовать кнопки "В корзину", "Купить в 1 клик"
- [ ] Реализовать модальное окно "Купить в 1 клик"
- [ ] Реализовать секцию отзывов
- [ ] Оптимизировать производительность
- [ ] Протестировать

**Задача 3.4.4:** Создать React Query hooks для каталога
- [ ] Создать `lib/hooks/useProducts.ts`:
  - `useProducts(filters)` - список товаров
  - `useProduct(slug)` - детали товара
  - `useCategories()` - категории
- [ ] Кэширование данных
- [ ] Инвалидация при обновлении
- [ ] Протестировать

### 🛒 3.5 Корзина

**Задача 3.5.1:** Создать страницу корзины
- [ ] Создать `app/cart/page.tsx`
- [ ] Список товаров в корзине
- [ ] Изменение количества (+/-)
- [ ] Удаление товара
- [ ] Показ цены за товар и общей суммы
- [ ] Применение промокода (поле ввода)
- [ ] Применение бонусов (слайдер или поле ввода)
- [ ] Итоговая сумма
- [ ] Кнопка "Оформить заказ"
- [ ] Пустая корзина (placeholder с анимацией)
- [ ] Протестировать

**Задача 3.5.2:** Создать компонент CartItem
- [ ] Создать `components/features/cart/CartItem.tsx`
- [ ] Изображение товара
- [ ] Название, цена
- [ ] Счетчик количества
- [ ] Кнопка удаления
- [ ] Анимация при удалении
- [ ] Протестировать

**Задача 3.5.3:** Создать React Query hooks для корзины
- [ ] Создать `lib/hooks/useCart.ts`:
  - `useCart()` - получение корзины
  - `useAddToCart()` - добавление в корзину
  - `useUpdateCartItem()` - обновление количества
  - `useRemoveCartItem()` - удаление товара
  - `useClearCart()` - очистка корзины
- [ ] Оптимистичные обновления
- [ ] Обработка ошибок
- [ ] Протестировать

### ✅ 3.6 Оформление заказа

**Задача 3.6.1:** Создать страницу оформления заказа
- [ ] Создать `app/checkout/page.tsx`
- [ ] Многошаговая форма (stepper):
  - Шаг 1: Корзина (краткий обзор)
  - Шаг 2: Доставка (тип доставки, адрес)
  - Шаг 3: Оплата (способ оплаты)
  - Шаг 4: Подтверждение
- [ ] Форма доставки:
  - Тип доставки (Radio: самовывоз/доставка)
  - Выбор магазина (если самовывоз, интеграция с картой)
  - Адрес доставки (если доставка, интеграция с картой для автозаполнения)
  - Комментарий
- [ ] Форма оплаты:
  - Тип оплаты (Radio: наличные/карта при получении/перевод/онлайн)
- [ ] Применение промокода
- [ ] Применение бонусов
- [ ] Расчет итоговой суммы
- [ ] Валидация всех полей
- [ ] Обработка ошибок
- [ ] Протестировать

**Задача 3.6.2:** Создать страницу подтверждения заказа
- [ ] Создать `app/orders/[id]/success/page.tsx`
- [ ] Номер заказа
- [ ] Статус заказа
- [ ] Информация о заказе
- [ ] Кнопка "Перейти к заказам"
- [ ] Кнопка "Вернуться в каталог"
- [ ] Протестировать

**Задача 3.6.3:** Создать React Query hooks для заказов
- [ ] Создать `lib/hooks/useOrders.ts`:
  - `useCreateOrder()` - создание заказа
  - `useOrder(id)` - детали заказа
  - `useOrders(filters)` - список заказов
- [ ] Обработка ошибок
- [ ] Протестировать

### 👤 3.7 Личный кабинет

**Задача 3.7.1:** Создать страницу профиля
- [ ] Создать `app/profile/page.tsx`
- [ ] Информация о пользователе (ФИО, телефон, email)
- [ ] Кнопка "Редактировать профиль"
- [ ] Баланс бонусов (с переходом на Bonus Screen)
- [ ] История заказов (краткий список с переходом на Order History)
- [ ] Адреса доставки (список с возможностью редактирования)
- [ ] Настройки (язык, уведомления)
- [ ] Кнопка "Выйти"
- [ ] Протестировать

**Задача 3.7.2:** Создать страницу истории заказов
- [ ] Создать `app/orders/page.tsx`
- [ ] Список заказов (с пагинацией)
- [ ] Фильтрация по статусу
- [ ] Сортировка по дате
- [ ] Pull to refresh
- [ ] Навигация на детальную страницу заказа
- [ ] Протестировать

**Задача 3.7.3:** Создать страницу деталей заказа
- [ ] Создать `app/orders/[id]/page.tsx`
- [ ] Полная информация о заказе
- [ ] Список товаров
- [ ] Статус заказа (с индикатором прогресса)
- [ ] Информация о доставке
- [ ] Информация об оплате
- [ ] Кнопка "Связаться с поддержкой" (опционально)
- [ ] Протестировать

**Задача 3.7.4:** Создать страницу бонусов
- [ ] Создать `app/bonus/page.tsx`
- [ ] Текущий баланс бонусов (крупно)
- [ ] История транзакций (список)
- [ ] Фильтрация по типу транзакции
- [ ] Пагинация
- [ ] Протестировать

### 🗺️ 3.8 Интеграция с картами

**Задача 3.8.1:** Настроить Yandex Maps API
- [ ] Установить `@pbe/react-yandex-maps` или использовать нативный API
- [ ] Создать компонент `components/features/maps/YandexMap.tsx`
- [ ] Настроить API ключ
- [ ] Реализовать отображение карты
- [ ] Реализовать маркеры магазинов
- [ ] Реализовать выбор магазина по клику на маркер
- [ ] Протестировать

**Задача 3.8.2:** Реализовать выбор магазина для самовывоза
- [ ] Создать компонент `components/features/stores/StoreSelector.tsx`
- [ ] Интеграция с картой
- [ ] Отображение списка магазинов
- [ ] Фильтрация по расстоянию
- [ ] Выбор магазина
- [ ] Протестировать

**Задача 3.8.3:** Реализовать автозаполнение адреса доставки
- [ ] Создать компонент `components/features/maps/AddressAutocomplete.tsx`
- [ ] Интеграция с Yandex Maps Geocoder API
- [ ] Автозаполнение адреса при вводе
- [ ] Получение координат
- [ ] Протестировать

### 📰 3.9 Блог и новости

**Задача 3.9.1:** Создать страницу блога
- [ ] Создать `app/blog/page.tsx`
- [ ] Список статей (grid)
- [ ] Фильтрация по категориям
- [ ] Фильтрация по тегам
- [ ] Поиск
- [ ] Пагинация
- [ ] SSG для SEO (generateStaticParams)
- [ ] Протестировать

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
- [ ] Создать `app/promotions/page.tsx`
- [ ] Список активных акций
- [ ] Таймер до конца акции
- [ ] Фильтрация по категориям
- [ ] Протестировать

**Задача 3.10.2:** Реализовать применение промокода
- [ ] Создать компонент `components/features/promotions/PromoCodeInput.tsx`
- [ ] Поле ввода промокода
- [ ] Валидация промокода
- [ ] Отображение скидки
- [ ] Применение к заказу
- [ ] Протестировать

### 🎨 3.11 Микроанимации и производительность

**Задача 3.11.1:** Реализовать микроанимации на главной странице
- [ ] Создать `app/page.tsx` (главная)
- [ ] Hero-блок с параллаксом (Framer Motion)
- [ ] Анимация появления элементов при скролле
- [ ] Плавные переходы
- [ ] Оптимизировать для 60 FPS
- [ ] Протестировать на мобильных устройствах

**Задача 3.11.2:** Реализовать плавные переходы между страницами
- [ ] Настроить `next-view-transitions` или использовать Framer Motion
- [ ] Анимация переходов
- [ ] Оптимизировать производительность
- [ ] Протестировать

**Задача 3.11.3:** Оптимизировать производительность
- [ ] Lazy loading изображений (next/image)
- [ ] Code splitting (динамические импорты)
- [ ] Оптимизация шрифтов (next/font)
- [ ] Минификация CSS и JS
- [ ] Провести Lighthouse аудит
- [ ] Исправить проблемы (цель: >85 Performance)
- [ ] Протестировать

### 🧪 3.12 Тестирование фронтенда

**Задача 3.12.1:** Настроить тестовое окружение
- [ ] Установить `@testing-library/react`, `@testing-library/jest-dom`
- [ ] Настроить Jest
- [ ] Создать test helpers
- [ ] Настроить mock для API

**Задача 3.12.2:** Написать unit тесты
- [ ] Тесты для компонентов (критичные)
- [ ] Тесты для hooks
- [ ] Тесты для утилит
- [ ] Coverage минимум 70%

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
