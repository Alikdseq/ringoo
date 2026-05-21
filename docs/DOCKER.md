# Docker — полный стек Ringoo

Все сервисы (PostgreSQL, Redis, Django, Celery, **Next.js**) запускаются одной командой из корня репозитория.

## Быстрый старт (разработка)

```bash
# 1. Переменные окружения
cp .env.example .env
cp backend/.env.example backend/.env.development
cp frontend/.env.docker.example frontend/.env.docker

# 2. Сборка и запуск
docker compose up -d --build

# 3. Миграции (первый раз)
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

| Сервис   | URL                         | Контейнер          |
|----------|-----------------------------|--------------------|
| Frontend | http://localhost:3000       | `ringoo_frontend`  |
| Backend  | http://localhost:8000       | `ringoo_backend`   |
| Admin    | http://localhost:8000/admin |                    |

## Архитектура URL API

- **Браузер** обращается к API по `NEXT_PUBLIC_API_V1_URL` → `http://localhost:8000/api/v1` (порт проброшен с контейнера `web`).
- **SSR Next.js** внутри Docker использует `API_INTERNAL_V1_URL` → `http://web:8000/api/v1` (сеть compose).

Не подставляйте `http://web:8000` в `NEXT_PUBLIC_*` — с хоста этот hostname недоступен.

## Полезные команды

```bash
# Логи
docker compose logs -f frontend
docker compose logs -f web

# Shell
docker compose exec frontend sh
docker compose exec web python manage.py shell

# Пересборка только фронта
docker compose build frontend
docker compose up -d frontend

# Остановка
docker compose down
```

Или через Makefile: `make up`, `make logs`, `make frontend-logs`.

## Production-сборка фронта

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

В корневом `.env` задайте боевые `NEXT_PUBLIC_API_V1_URL` и `NEXT_PUBLIC_SITE_URL` до сборки образа `frontend`.

## Windows / hot reload

В `docker-compose.yml` включены `WATCHPACK_POLLING` и `CHOKIDAR_USEPOLLING` для стабильного HMR при volume mount.

`node_modules` хранится в именованном volume `frontend_node_modules`, чтобы не перетирать зависимости с хоста.

## Манифесты статики

При старте контейнера `frontend` entrypoint пытается сгенерировать `magazins/manifest.json` и `menegers/manifest.json`, если есть папки в `public/`.

Вручную:

```bash
docker compose exec frontend npm run magazins:manifest
docker compose exec frontend npm run menegers:manifest
```

## Сообщения Chrome в консоли (не баг приложения)

### «Не удается добавить файловую систему: &lt;illegal path&gt;»

Сообщение из **Chrome DevTools** (Sources → Workspace / сопоставление с диском), не из Next.js или Django. Частые причины:

- расширения браузера (React DevTools, блокировщики, VPN);
- попытка привязать папку проекта с недопустимым путём (сетевой диск, симлинк, путь с особыми символами на Windows).

**Что делать:** откройте сайт в режиме инкогнито без расширений или игнорируйте, если сайт работает. На работу `localhost:3000` это не влияет.

### «preloaded using link preload but not used»

Предупреждение, если браузер заранее подгрузил ресурс (`rel=preload`), а страница его не использовала в первые секунды. В Ringoo это обычно:

- несколько `priority` у `next/image` на одной странице;
- фон hero в режиме «Свой», когда в localStorage другой режим, чем в cookie (исправлено синхронизацией `UiModeProvider` с bootstrap-скриптом).

После правок остаётся один приоритетный LCP на главной (фон hero в официальном режиме). Шрифты Geist: `preload: false` в `layout.tsx`.
