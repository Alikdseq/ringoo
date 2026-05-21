.PHONY: help up down restart logs shell migrate makemigrations test lint frontend-dev frontend-logs frontend-shell frontend-build frontend-lint frontend-test build build-prod clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make up              - Запустить весь стек (db, redis, web, frontend, celery)"
	@echo "  make down            - Остановить все сервисы"
	@echo "  make restart         - Перезапустить все сервисы"
	@echo "  make logs            - Логи всех сервисов"
	@echo "  make shell           - Django shell"
	@echo "  make migrate         - Миграции БД"
	@echo "  make makemigrations  - Создать миграции"
	@echo "  make test            - Тесты backend"
	@echo "  make lint            - Линтеры backend"
	@echo "  make lint-fix        - Автоисправление линтеров backend"
	@echo "  make frontend-logs   - Логи Next.js (контейнер frontend)"
	@echo "  make frontend-shell  - Shell в контейнере frontend"
	@echo "  make frontend-build  - npm run build в контейнере"
	@echo "  make build           - docker compose build"
	@echo "  make build-prod      - Production-образы"
	@echo "  make clean           - Очистить volumes и кэш"
	@echo "  make superuser        - Создать суперпользователя Django"
	@echo "  make backup           - Полный бэкап БД + медиа (см. docs/BACKUP.md)"
	@echo "  make backup-db        - Бэкап только БД"
	@echo "  make backup-media     - Бэкап только медиафайлов"

# Docker Compose commands
COMPOSE ?= docker compose

up:
	$(COMPOSE) up -d
	@echo "Сервисы запущены."
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend:  http://localhost:8000"

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f

# Django commands
shell:
	$(COMPOSE) exec web python manage.py shell

migrate:
	$(COMPOSE) exec web python manage.py migrate

makemigrations:
	$(COMPOSE) exec web python manage.py makemigrations

superuser:
	$(COMPOSE) exec web python manage.py createsuperuser

# Testing
test:
	$(COMPOSE) exec web pytest

test-coverage:
	$(COMPOSE) exec web pytest --cov=. --cov-report=html --cov-report=term

# Linting
lint:
	$(COMPOSE) exec web black --check .
	$(COMPOSE) exec web isort --check-only .
	$(COMPOSE) exec web flake8 .
	$(COMPOSE) exec web mypy . --ignore-missing-imports || true

lint-fix:
	$(COMPOSE) exec web black .
	$(COMPOSE) exec web isort .

# Frontend (Docker)
frontend-dev:
	$(COMPOSE) logs -f frontend

frontend-logs:
	$(COMPOSE) logs -f frontend

frontend-shell:
	$(COMPOSE) exec frontend sh

frontend-build:
	$(COMPOSE) exec frontend npm run build

frontend-lint:
	$(COMPOSE) exec frontend npm run lint

frontend-test:
	$(COMPOSE) exec frontend npm test

# Build
build:
	$(COMPOSE) build

build-prod:
	$(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml build

# Cleanup
clean:
	$(COMPOSE) down -v
	docker system prune -f
	@echo "Volumes и кэш очищены"

clean-all: clean
	$(COMPOSE) down --rmi all -v
	@echo "Все образы и volumes удалены"

# Database commands
db-shell:
	$(COMPOSE) exec db psql -U postgres -d ringoo

db-test:
	$(COMPOSE) exec web python test_db_connection.py

db-reset:
	$(COMPOSE) down -v
	$(COMPOSE) up -d db
	sleep 5
	make migrate

# Redis commands
redis-cli:
	$(COMPOSE) exec redis redis-cli

redis-test:
	$(COMPOSE) exec web python test_redis_connection.py

redis-ping:
	$(COMPOSE) exec redis redis-cli ping

# Celery commands
celery-logs:
	$(COMPOSE) logs -f celery

celery-beat-logs:
	$(COMPOSE) logs -f celery-beat

celery-test:
	$(COMPOSE) exec web python test_celery.py

celery-shell:
	$(COMPOSE) exec celery celery -A config.celery shell

celery-inspect:
	$(COMPOSE) exec celery celery -A config.celery inspect active

# Sentry commands
sentry-test:
	$(COMPOSE) exec web python test_sentry.py

# Health check
health:
	@echo "Checking services health..."
	@$(COMPOSE) ps

# Backup (см. docs/BACKUP.md)
backup:
	@bash scripts/backup-all.sh

backup-db:
	@bash scripts/backup-db.sh

backup-media:
	@bash scripts/backup-media.sh

restore-db:
	@if [ -z "$(DUMP)" ]; then echo "Usage: make restore-db DUMP=backups/ringoo_db_YYYYMMDD_HHMMSS.sql.gz"; exit 1; fi
	@bash scripts/restore-db.sh "$(DUMP)" --drop

restore-media:
	@if [ -z "$(ARCHIVE)" ]; then echo "Usage: make restore-media ARCHIVE=backups/ringoo_media_YYYYMMDD_HHMMSS.tar.gz"; exit 1; fi
	@bash scripts/restore-media.sh "$(ARCHIVE)"
