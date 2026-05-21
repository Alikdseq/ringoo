# Docker: запуск backend и frontend

Этот файл описывает рабочий сценарий запуска проекта через Docker в текущей структуре репозитория.

## 1) Подготовка

Из корня проекта `c:\ringoo`:

```powershell
Copy-Item backend/.env.example backend/.env.development -ErrorAction SilentlyContinue
Copy-Item frontend/.env.example frontend/.env.local -ErrorAction SilentlyContinue
```

Если файлы уже существуют, команды можно пропустить.

## 2) Запуск backend-стека через Docker Compose

В проекте уже настроены сервисы:
- `db` (PostgreSQL)
- `redis`
- `web` (Django)
- `celery`
- `celery-beat`

Запуск:

```powershell
docker compose up -d
```

Проверка статуса:

```powershell
docker compose ps
```

Применить миграции:

```powershell
docker compose exec web python manage.py migrate
```

Создать суперпользователя (опционально):

```powershell
docker compose exec web python manage.py createsuperuser
```

Логи backend:

```powershell
docker compose logs -f web
```

Backend будет доступен на `http://localhost:8000`.

## 3) Запуск frontend через Docker (Node container)

Отдельного frontend-сервиса в `docker-compose.yml` сейчас нет, поэтому фронтенд запускается в отдельном контейнере Node.

### Dev-режим (Next.js)

Из корня проекта:

```powershell
docker run --rm -it `
  -p 3000:3000 `
  -v "${PWD}\frontend:/app" `
  -w /app `
  node:20-alpine `
  sh -c "npm install && npm run dev -- --hostname 0.0.0.0 --port 3000"
```

Frontend будет доступен на `http://localhost:3000`.

### Production-проверка (build + start)

```powershell
docker run --rm -it `
  -p 3000:3000 `
  -v "${PWD}\frontend:/app" `
  -w /app `
  node:20-alpine `
  sh -c "npm install && npm run build && npm run start -- -H 0.0.0.0 -p 3000"
```

## 4) Остановка

Остановить backend-стек:

```powershell
docker compose down
```

Остановить frontend-контейнер:
- `Ctrl + C` в терминале, где запущен `docker run`.

## 5) Полезные команды

Перезапуск backend:

```powershell
docker compose restart
```

Логи всех сервисов:

```powershell
docker compose logs -f
```

Полная очистка (контейнеры + volumes):

```powershell
docker compose down -v
```
