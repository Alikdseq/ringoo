# Настройка GitHub Secrets для CI/CD

## Обзор

GitHub Secrets используются для хранения чувствительных данных в CI/CD pipeline.

## Настройка Secrets

### Где настроить

1. Перейдите в репозиторий на GitHub
2. Settings → Secrets and variables → Actions
3. Нажмите "New repository secret"

### Необходимые Secrets

#### Backend Secrets

| Secret Name | Описание | Пример |
|------------|----------|--------|
| `DB_NAME` | Имя базы данных для тестов | `ringoo_test` |
| `DB_USER` | Пользователь БД | `postgres` |
| `DB_PASSWORD` | Пароль БД | `test_password` |
| `SECRET_KEY` | Django SECRET_KEY | `django-insecure-test-key` |
| `SENTRY_DSN` | Sentry DSN (опционально) | `https://...@sentry.io/...` |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/0` |

#### Frontend Secrets

| Secret Name | Описание | Пример |
|------------|----------|--------|
| `NEXT_PUBLIC_API_URL` | URL API для сборки | `http://localhost:8000` |

#### Deployment Secrets (для production)

| Secret Name | Описание |
|------------|----------|
| `DEPLOY_HOST` | IP адрес сервера |
| `DEPLOY_USER` | Пользователь для SSH |
| `DEPLOY_SSH_KEY` | Приватный SSH ключ |
| `DEPLOY_PATH` | Путь на сервере (`/opt/ringoo`) |

## Использование в GitHub Actions

Secrets доступны через `${{ secrets.SECRET_NAME }}`:

```yaml
env:
  DATABASE_URL: postgresql://postgres:${{ secrets.DB_PASSWORD }}@localhost:5432/${{ secrets.DB_NAME }}
  SECRET_KEY: ${{ secrets.SECRET_KEY }}
```

## Безопасность

⚠️ **Важно:**
- Никогда не коммитьте секреты в репозиторий
- Используйте разные секреты для разных окружений
- Регулярно ротируйте секреты
- Используйте минимальные права доступа

## Проверка секретов

Pre-commit hook `detect-secrets` автоматически проверяет что секреты не попали в код.

---

**Дата создания:** 2026-02-05
