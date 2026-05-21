# CI/CD Pipeline Documentation

## Обзор

Проект использует GitHub Actions для автоматизации CI/CD процессов.

## Workflows

### 1. Backend CI (`backend-ci.yml`)

Запускается при изменениях в `backend/` директории.

**Jobs:**
- **lint** - Проверка кода линтерами:
  - Black (форматирование)
  - isort (сортировка импортов)
  - Flake8 (стиль кода)
  - MyPy (проверка типов)
- **test** - Запуск тестов:
  - PostgreSQL и Redis сервисы
  - Миграции БД
  - Pytest с покрытием кода
  - Загрузка coverage в Codecov
- **security** - Сканирование безопасности:
  - Bandit (поиск уязвимостей)

### 2. Frontend CI (`frontend-ci.yml`)

Запускается при изменениях в `frontend/` директории.

**Jobs:**
- **lint** - Проверка кода:
  - ESLint
  - Prettier
- **type-check** - Проверка типов TypeScript
- **test** - Запуск тестов:
  - Jest с покрытием кода
  - Загрузка coverage в Codecov
- **build** - Сборка приложения:
  - Next.js production build
  - Сохранение артефактов

### 3. PR Check (`pr-check.yml`)

Запускается при создании Pull Request.

**Jobs:**
- **backend-check** - Проверка backend изменений:
  - Линтеры
  - Тесты
- **frontend-check** - Проверка frontend изменений:
  - Линтеры
  - Type check
  - Тесты
  - Build check

## Конфигурация линтеров

### Backend

#### Black
- Конфигурация: `backend/pyproject.toml`
- Длина строки: 120 символов
- Целевая версия Python: 3.11

#### isort
- Конфигурация: `backend/.isort.cfg`
- Профиль: black
- Длина строки: 120 символов

#### Flake8
- Конфигурация: `backend/.flake8`
- Максимальная длина строки: 120
- Максимальная сложность: 10
- Игнорируемые директории: migrations, venv

#### MyPy
- Конфигурация: `backend/pyproject.toml`
- Режим: нестрогий (ignore_missing_imports)
- Проверка типов для Django модулей отключена

#### Bandit
- Конфигурация: `backend/.bandit`
- Исключения: migrations, venv, tests

### Frontend

#### ESLint
- Конфигурация: `frontend/.eslintrc.json`
- Расширения: Next.js, TypeScript, Prettier
- Правила: стандартные + кастомные

#### Prettier
- Конфигурация: `frontend/.prettierrc.json`
- Длина строки: 100 символов
- Одинарные кавычки: да
- Табы: пробелы (2)

## Локальный запуск

### Backend

```bash
cd backend

# Форматирование кода
black .

# Сортировка импортов
isort .

# Проверка стиля
flake8 .

# Проверка типов
mypy . --ignore-missing-imports

# Запуск тестов
pytest

# Проверка безопасности
bandit -r .
```

### Frontend

```bash
cd frontend

# Проверка ESLint
npm run lint

# Исправление ESLint ошибок
npm run lint:fix

# Проверка форматирования
npm run format:check

# Форматирование кода
npm run format

# Проверка типов
npm run type-check

# Запуск тестов
npm test

# Сборка
npm run build
```

## Триггеры

### Push события
- Ветки: `develop`, `staging`, `main`
- Пути: изменения в соответствующих директориях

### Pull Request события
- Ветки: `develop`, `staging`, `main`
- Автоматическая проверка всех изменений

## Переменные окружения

### Secrets (настраиваются в GitHub)

- `NEXT_PUBLIC_API_URL` - URL API для frontend сборки
- `CODECOV_TOKEN` - токен для загрузки coverage (опционально)

## Troubleshooting

### Линтеры не проходят

1. Запустите линтеры локально
2. Исправьте ошибки автоматически (где возможно)
3. Проверьте конфигурационные файлы

### Тесты падают

1. Проверьте локально: `pytest` или `npm test`
2. Проверьте переменные окружения
3. Убедитесь, что миграции применены

### Build не проходит

1. Проверьте локально: `npm run build`
2. Проверьте переменные окружения
3. Проверьте логи сборки

---

**Важно**: Все проверки должны проходить перед merge в защищенные ветки!
