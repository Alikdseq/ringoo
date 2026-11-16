# RELEASE 6 — Полная локальная проверка CI перед Push

**Дата / время:** 2026-11-14 16:21:39 +03:00  
**Проект:** `C:\ringoo`  
**Ветка:** `main`  
**HEAD:** `fcc23d001ddea397e152adde4ea4c86f25ff74e3` (= ожидаемый)  
**Режим:** READ-ONLY / DIAGNOSTICS ONLY  
**Основание:** RELEASE 4 = PASS WITH RISKS; RELEASE 5 = READY WITH CONDITIONS  

**Не выполнялось:** git write, fetch/push/pull, format/fix, pip/npm install, migrate/APPLY/deploy.

---

## Итоговый вердикт

# **BLOCKED**

Обязательные шаги GitHub Actions, воспроизведённые локально, **падают**:

| Job | Падающие шаги |
|---|---|
| `backend-ci` lint | Black, isort, flake8, mypy |
| `frontend-ci` lint | Prettier `format:check` |
| `frontend-ci` test | `test:coverage` (пороги coverage) |

Функциональные pytest / `npm run lint` / tsc / build — зелёные, но **этого недостаточно** для READY FOR PUSH.

---

## 1. Исходное состояние (BLOCK 1)

| Проверка | Результат |
|---|---|
| CWD | `C:\ringoo` |
| Branch | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| Upstream | `origin/main` |
| Log −9 | 9 коммитов RELEASE 3 на месте |
| Status | exclude/HOLD + отчёты R3–R5 (не в коммитах) |

---

## 2. Backend CI (BLOCK 2)

Источник команд: `.github/workflows/backend-ci.yml`.

| Проверка | Команда | Exit | Результат | Эквивалентность CI |
|---|---|---:|---|---|
| Black | `python -m black --check --diff .` | **1** | **FAIL** — `190 files would be reformatted`, 147 unchanged | **да** (та же команда) |
| isort | `python -m isort --check-only --diff .` | **1** | **FAIL** — config: `THIRDPARTY` / `sentry_sdk` not in sections | **да** (падает до diff) |
| flake8 | `python -m flake8 . --count --statistics` | **1** | **FAIL** — `ValueError: Error code '#' supplied to 'ignore'` в `.flake8` (inline comments) | **да** (тот же `.flake8`) |
| mypy | `python -m mypy . --config-file=pyproject.toml` | **1** | **FAIL** — **167 errors** in 49 files | **да** |
| Django check | `manage.py check` (`config.settings.test`) | 0 | PASS | доп. (не в lint job) |
| makemigrations | `--check --dry-run` | 0 | PASS | доп. |
| pytest | `pytest tests apps --ds=config.settings.test -q --cov=. --cov-report=term` | 0 | **476 passed, 8 skipped** (~96s) | **частично** — CI: Postgres 15 + Redis + `DATABASE_URL`/`REDIS_URL`; локально SQLite `:memory:` |

### Black — детали

- Всего: **190** файлов требуют reformat.
- Среди `.py` из `b3a9db4..HEAD`: **54 / 62** тоже не проходят `black --check`.
- Пример diff: `tests/test_yookassa_payments.py` (переносы строк).

### isort — детали

```
ERROR: Found sentry_sdk import while parsing, but THIRDPARTY was not included
in the `sections` setting of your config.
```

`[tool.isort]` в `pyproject.toml`: `profile = "black"` без явных `sections` / `known_third_party` — конфиг ломает проверку.

### flake8 — детали

Файл `backend/.flake8`:

```ini
ignore =
    E203,  # whitespace before ':'
    ...
```

Новый flake8 отвергает `#` как «код» в `ignore`. Job lint **не стартует**.

### mypy — детали

- `Found 167 errors in 49 files (checked 337 source files)`.
- Примеры: `apps/users/views.py`, settings `used-before-def`, тесты payments/bonus.
- Лог: `backend/var/r6/mypy.txt` (gitignore `var/` / локальный артефакт).

### pytest vs CI Postgres

| | Local R6 | GitHub backend-ci test |
|---|---|---|
| DB | SQLite `:memory:` | PostgreSQL 15 service |
| Redis | DummyCache / test settings | Redis 7 service |
| migrate before tests | нет (DisableMigrations) | `manage.py migrate` на CI DB |
| Результат | 476/8 skip | **не воспроизведено 1:1** |

**Не заявляем эквивалентность** Postgres/Redis concurrency.

---

## 3. Frontend CI (BLOCK 3)

Источник: `.github/workflows/frontend-ci.yml` + `frontend/package.json`.

| Проверка | Команда | Exit | Результат | Эквивалентность CI |
|---|---|---:|---|---|
| ESLint | `npm run lint` (= `eslint .`) | **0** | PASS — **0 errors, 119 warnings** | **да** |
| Prettier | `npm run format:check` | **1** | **FAIL** — style issues in **74** files | **да** |
| TypeScript | `npm run type-check` | 0 | PASS | **да** |
| Tests+coverage | `npm run test:coverage` | **1** | Tests идут; **FAIL** thresholds: functions 25.74% &lt; 30%, branches 26.95% &lt; 30% | **да** |
| Build | `npm run build` | 0 | PASS | **да** |
| npm audit | `npm audit --omit=dev --audit-level=high` | **0** | PASS — 5 **moderate** (ниже high) | **да** |

### ESLint warnings (RELEASE 4)

119 warnings **не** валят `npm run lint` (нет `--max-warnings 0`).  
Разница с R4: там сознательно запускали `eslint --max-warnings 0` → exit 1.

### Prettier

- 74 файла; **37** из диапазона RELEASE 3, **37** уже вне диапазона (pre-existing на дереве).
- CI `format:check` упадёт на push в `main` с изменениями `frontend/**`.

### test:coverage vs R4

| | R4 | R6 / CI |
|---|---|---|
| Команда | `npm run test -- --run` | `npm run test:coverage` |
| Результат | 154 passed | coverage threshold **FAIL** |

---

## 4. Pre-commit vs Actions vs R4 (BLOCK 4)

| Проверка | pre-commit | GitHub Actions | R4 | R6 |
|---|---|---|---|---|
| Black | да (modify) | `--check --diff` | не | **FAIL** |
| isort | да | `--check-only --diff` | не | **FAIL** |
| flake8 | да | `--count --statistics` | не | **FAIL** (config) |
| mypy | да | `pyproject.toml` | не | **FAIL** |
| ESLint | `--max-warnings=0` | `npm run lint` (без max) | max=0 fail; CI-эквив. не | **PASS** (CI-эквив.) |
| Prettier | да | `format:check` | не | **FAIL** |
| pytest | — | PG+Redis | SQLite PASS | SQLite PASS +cov |
| Vitest | — | `test:coverage` | `test --run` PASS | **coverage FAIL** |
| build / tsc | — | да | PASS | PASS |
| npm audit | — | high+ | не | PASS |

---

## 5. Сводная матрица (BLOCK 5)

| Проверка | Команда | Результат | Ошибки | Эквивалентность CI |
|---|---|---|---|---|
| Black | `black --check --diff .` | **FAIL** | 190 files | да |
| isort | `isort --check-only --diff .` | **FAIL** | config THIRDPARTY | да |
| flake8 | `flake8 . --count --statistics` | **FAIL** | `.flake8` `#` in ignore | да |
| mypy | `mypy . --config-file=pyproject.toml` | **FAIL** | 167 errors / 49 files | да |
| pytest | `pytest … --cov` (test settings) | **PASS** | 0 fail / 8 skip | частично (не PG) |
| npm lint | `npm run lint` | **PASS** | 119 warnings | да |
| Prettier | `npm run format:check` | **FAIL** | 74 files | да |
| TypeScript | `npm run type-check` | **PASS** | 0 | да |
| Frontend tests | `npm run test:coverage` | **FAIL** | coverage thresholds | да |
| Next build | `npm run build` | **PASS** | 0 | да |
| npm audit | `audit --omit=dev --audit-level=high` | **PASS** | 5 moderate | да |

### Прошли

Django check, makemigrations check, pytest (SQLite), npm lint, tsc, build, npm audit (high+).

### Упали

Black, isort, flake8, mypy, Prettier, Vitest coverage thresholds.

### Неполностью / не эквивалентно

pytest без PostgreSQL 15 / Redis CI services; backend `migrate` на CI DB не гонялся.

---

## 6. Классификация проблем (BLOCK 6)

| ID | Уровень | Описание |
|---|---|---|
| R6-001 | **BLOCKER** | Black `--check` fail (190 файлов; 54 в RELEASE range) → backend-ci lint |
| R6-002 | **BLOCKER** | isort config crash → backend-ci lint |
| R6-003 | **BLOCKER** | flake8 `.flake8` invalid ignore comments → backend-ci lint |
| R6-004 | **BLOCKER** | mypy 167 errors → backend-ci lint |
| R6-005 | **BLOCKER** | Prettier `format:check` 74 files → frontend-ci lint |
| R6-006 | **BLOCKER** | `test:coverage` ниже порогов functions/branches → frontend-ci test |
| R6-007 | **HIGH** | Pytest CI на Postgres/Redis не воспроизведён |
| R6-008 | **INFO** | 119 ESLint warnings не валят CI `npm run lint` |
| R6-009 | **INFO** | npm audit: только moderate при `--audit-level=high` |
| R6-010 | **LOW** | Локальные артефакты cov/htmlcov (gitignore) |

Часть FAIL (Prettier вне range, black/mypy по всему дереву) может быть **pre-existing** на remote `b3a9db4`. Это не отменяет: **push текущей tip всё равно запустит красные lint/test jobs**.

---

## 7. Риски перед Push

1. `backend-ci` lint job почти наверняка **красный**.  
2. `frontend-ci` lint (Prettier) и test (coverage) почти наверняка **красные**.  
3. Branch protection с required checks заблокирует merge/зелёный статус.  
4. Исправления потребуют отдельного этапа (format/config/thresholds) — **не** в рамках R6.  
5. Даже после зелёного Actions: staging migrate `stores.0008`/`0009` остаётся ops-шагом.

---

## 8. Рекомендации следующего этапа

1. **Не push** до отдельного fix-pass:  
   - починить `.flake8` ignore (убрать inline `#`);  
   - починить isort `sections` / THIRDPARTY;  
   - `black` + Prettier на затронутых файлах (отдельное разрешение);  
   - политика mypy / coverage thresholds.  
2. Либо push осознанно на красный CI (только если branch protection позволяет и это приемлемо).  
3. После format-fix — повторить RELEASE 6 smoke.  
4. Отдельно: Postgres pytest при наличии disposable DB.

---

## 9. Состояние после диагностики

| | |
|---|---|
| HEAD | **не изменился** `fcc23d0…` |
| Исходники / lockfiles | **не менялись** |
| `git status` extras | прежние exclude/HOLD + R3–R5 reports; **+ этот R6 report** после записи |
| Артефакты диагностики | `backend/var/r6/*.txt`, `backend/htmlcov/`, `backend/coverage.xml`, `frontend/coverage/` — **gitignore**, не для commit |

---

## Остановка

Исправления / commit / push / fetch / deploy / migrate / APPLY — **не выполнялись**.  
Ждать отдельного решения.
