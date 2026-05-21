# Руководство по внесению вклада

Спасибо за интерес к проекту Ringoo! Мы рады вашему вкладу.

## Как внести вклад

### 1. Форк и клонирование

```bash
# Форкните репозиторий на GitHub
# Затем клонируйте ваш форк
git clone https://github.com/your-username/ringoo.git
cd ringoo
```

### 2. Создание ветки

```bash
# Переключитесь на develop
git checkout develop
git pull origin develop

# Создайте feature ветку
git checkout -b feature/your-feature-name
```

### 3. Настройка окружения

```bash
# Запустить сервисы
make up

# Применить миграции (в т.ч. django-axes после `git pull`)
make migrate

# Установить pre-commit hooks
pre-commit install
```

### 4. Разработка

- Следуйте стандартам кодирования проекта
- Пишите понятные комментарии
- Добавляйте тесты для новой функциональности
- Обновляйте документацию при необходимости

### 5. Коммиты

Используйте [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Примеры
git commit -m "feat(backend): добавить модель Product"
git commit -m "fix(api): исправить валидацию телефона"
git commit -m "docs(readme): обновить инструкции"
```

### 6. Тестирование

```bash
# Запустить тесты backend
make test

# Запустить линтеры
make lint

# Проверить форматирование
make lint-fix
```

### 7. Pull Request

1. Убедитесь что все тесты проходят
2. Убедитесь что код соответствует стандартам
3. Создайте Pull Request в ветку `develop`
4. Заполните шаблон PR
5. Дождитесь code review

## Стандарты кодирования

### Python (Backend)

- Используйте `black` для форматирования
- Используйте `isort` для сортировки импортов
- Следуйте PEP 8
- Используйте type hints где возможно
- Покрывайте код тестами (минимум 80% для критичных модулей)

### TypeScript/JavaScript (Frontend)

- Используйте ESLint и Prettier
- Следуйте правилам Next.js
- Используйте TypeScript для типобезопасности
- Компоненты должны быть переиспользуемыми

## Структура коммитов

Формат: `<type>(<scope>): <subject>`

**Типы:**
- `feat` - новая функциональность
- `fix` - исправление бага
- `docs` - документация
- `style` - форматирование
- `refactor` - рефакторинг
- `test` - тесты
- `chore` - вспомогательные задачи

**Область:**
- `backend` - изменения в Django
- `frontend` - изменения в Next.js
- `api` - изменения в API
- `config` - конфигурация

## Тестирование

### Backend

```bash
# Запустить все тесты
pytest

# С покрытием
pytest --cov=. --cov-report=html

# Конкретный тест
pytest apps/users/tests/test_models.py
```

### Frontend

```bash
cd frontend
npm test
```

## Code Review

Все Pull Requests проходят code review. Ожидайте:
- Комментарии и предложения
- Запросы на изменения
- Обсуждение решений

## Вопросы?

Если у вас есть вопросы:
- Создайте Issue в репозитории
- Свяжитесь с командой разработки

---

**Спасибо за ваш вклад!** 🎉
