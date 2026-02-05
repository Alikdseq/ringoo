# Правила защиты веток

## Ветки и их назначение

### `main` (production)
- **Назначение**: Продакшн версия приложения
- **Защита**: 
  - Требуется PR с минимум 1 approval
  - Требуется прохождение всех CI проверок
  - Прямые коммиты запрещены
  - Требуется code review
  - Запрещено force push

### `staging`
- **Назначение**: Предпродакшн окружение для финального тестирования
- **Защита**:
  - Требуется PR с минимум 1 approval
  - Требуется прохождение всех CI проверок
  - Прямые коммиты запрещены (кроме hotfix)

### `develop`
- **Назначение**: Основная ветка разработки
- **Защита**:
  - Требуется прохождение базовых CI проверок (lint, tests)
  - Прямые коммиты разрешены для разработчиков команды

## Workflow

### Разработка новой функциональности
1. Создать feature ветку от `develop`: `git checkout -b feature/task-name`
2. Разработать функциональность
3. Создать PR в `develop`
4. После ревью и merge в `develop` - функциональность доступна в dev окружении

### Релиз в staging
1. Создать PR из `develop` в `staging`
2. После прохождения тестов и approval - merge
3. Деплой на staging окружение

### Релиз в production
1. Создать PR из `staging` в `main`
2. Обязательное approval от lead developer
3. После merge - автоматический деплой на production

### Hotfix
1. Создать hotfix ветку от `main`: `git checkout -b hotfix/issue-description`
2. Исправить проблему
3. Создать PR в `main` (с пометкой [HOTFIX])
4. После merge в `main` - создать PR в `develop` и `staging` для синхронизации

## Настройка в GitHub/GitLab

### Для ветки `main`:
- Require pull request reviews before merging: ✅ (минимум 1)
- Require status checks to pass before merging: ✅
- Require branches to be up to date before merging: ✅
- Require conversation resolution before merging: ✅
- Do not allow bypassing the above settings: ✅
- Restrict pushes that create files larger than 100 MB: ✅

### Для ветки `staging`:
- Require pull request reviews before merging: ✅ (минимум 1)
- Require status checks to pass before merging: ✅
- Require conversation resolution before merging: ✅

### Для ветки `develop`:
- Require status checks to pass before merging: ✅
- Allow force pushes: ❌
- Allow deletions: ❌

## Исключения

В экстренных случаях (критичные баги в production) разрешается:
- Прямой коммит в `main` с последующим созданием hotfix PR
- Обязательное уведомление команды в Slack/Telegram
- Пост-мортем обсуждение для предотвращения повторения
