# Настройка Pre-commit Hooks

## Установка

```bash
# Установить pre-commit
pip install pre-commit

# Или через requirements-dev.txt
pip install -r backend/requirements-dev.txt
```

## Активация hooks

```bash
# Установить hooks в git
pre-commit install

# Установить hooks для commit-msg
pre-commit install --hook-type commit-msg
```

## Использование

Hooks автоматически запускаются при каждом коммите:

```bash
git commit -m "feat: добавить новую функцию"
# Pre-commit hooks запустятся автоматически
```

## Ручной запуск

```bash
# Проверить все файлы
pre-commit run --all-files

# Проверить конкретный файл
pre-commit run --files backend/apps/users/models.py

# Пропустить hooks (не рекомендуется)
git commit --no-verify -m "message"
```

## Настроенные hooks

### Python

- **black** - Форматирование кода
- **isort** - Сортировка импортов
- **flake8** - Линтинг
- **mypy** - Проверка типов

### Security

- **detect-secrets** - Поиск секретов в коде
- **detect-private-key** - Поиск приватных ключей

### Frontend

- **ESLint** - Линтинг JavaScript/TypeScript
- **Prettier** - Форматирование кода

### General

- **trailing-whitespace** - Удаление пробелов в конце строк
- **end-of-file-fixer** - Добавление новой строки в конце файла
- **check-yaml** - Проверка YAML файлов
- **check-json** - Проверка JSON файлов

## Обновление hooks

```bash
# Обновить все hooks до последних версий
pre-commit autoupdate
```

## Troubleshooting

### Проблема: Hook не запускается

```bash
# Переустановить hooks
pre-commit uninstall
pre-commit install
```

### Проблема: Hook слишком медленный

```bash
# Запустить только для измененных файлов (по умолчанию)
# Или исключить определенные файлы в .pre-commit-config.yaml
```

### Проблема: Hook требует зависимости

```bash
# Установить зависимости
pip install -r backend/requirements-dev.txt
cd frontend && npm install
```

---

**Дата создания:** 2026-02-05
