# Git Workflow для проекта Ringoo

## Быстрая настройка

После клонирования репозитория выполните:

```bash
# Настроить шаблон коммитов для этого репозитория
git config --local commit.template .gitmessage

# Проверить настройки
git config --local --list
```

## Структура веток

- **main** - production версия (стабильная)
- **staging** - предпродакшн окружение
- **develop** - основная ветка разработки
- **feature/** - ветки для новых функций
- **hotfix/** - ветки для критичных исправлений
- **bugfix/** - ветки для исправления багов

## Рабочий процесс

### 1. Создание feature ветки

```bash
# Переключиться на develop
git checkout develop

# Обновить develop
git pull origin develop

# Создать новую feature ветку
git checkout -b feature/task-name

# Или для bugfix
git checkout -b bugfix/issue-description
```

### 2. Работа над задачей

```bash
# Делать коммиты с использованием conventional commits
git add .
git commit -m "feat(backend): добавить модель Product"

# Периодически синхронизировать с develop
git fetch origin
git rebase origin/develop
```

### 3. Создание Pull Request

1. Запушить ветку: `git push origin feature/task-name`
2. Создать PR в GitHub/GitLab в ветку `develop`
3. Дождаться code review
4. Исправить замечания (если есть)
5. После approval - merge

### 4. После merge

```bash
# Вернуться на develop
git checkout develop

# Обновить локальную ветку
git pull origin develop

# Удалить локальную feature ветку
git branch -d feature/task-name
```

## Формат коммитов

Используйте [Conventional Commits](.github/COMMIT_CONVENTION.md):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Примеры:

```bash
# Простой коммит
git commit -m "feat(backend): добавить модель Product"

# Коммит с описанием
git commit -m "fix(api): исправить валидацию телефона

Исправлена проблема с валидацией российских номеров.
Теперь корректно обрабатываются номера с кодом +7.

Closes #123"

# Breaking change
git commit -m "feat(api)!: изменить формат ответа

BREAKING CHANGE: формат ответа изменен с массива на объект"
```

## Правила защиты веток

Подробности в [.github/BRANCH_PROTECTION.md](../.github/BRANCH_PROTECTION.md)

## Полезные команды

```bash
# Просмотр истории коммитов
git log --oneline --graph --all

# Просмотр изменений
git diff

# Статус репозитория
git status

# Просмотр веток
git branch -a

# Синхронизация с удаленным репозиторием
git fetch origin
git pull origin develop

# Отмена последнего коммита (сохранить изменения)
git reset --soft HEAD~1

# Отмена последнего коммита (удалить изменения)
git reset --hard HEAD~1
```

## Troubleshooting

### Конфликты при rebase

```bash
# Если возникли конфликты
git rebase --abort  # Отменить rebase
# Или разрешить конфликты и продолжить
git add .
git rebase --continue
```

### Откат изменений

```bash
# Откатить изменения в файле
git checkout -- <file>

# Откатить все изменения
git reset --hard HEAD
```

---

**Важно**: Всегда синхронизируйтесь с `develop` перед созданием PR!
