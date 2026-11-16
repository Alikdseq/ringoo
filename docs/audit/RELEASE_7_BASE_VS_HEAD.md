# RELEASE 7 — Сравнительный аудит CI: BASE vs HEAD

**Дата / время:** 2026-11-14 16:39 +03:00  
**Проект:** `C:\ringoo`  
**Ветка:** `main` (не переключалась)  
**BASE:** `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8`  
**HEAD:** `fcc23d001ddea397e152adde4ea4c86f25ff74e3`  
**Основание:** RELEASE 6 = BLOCKED  
**Режим:** READ-ONLY (archive в `%TEMP%`, без checkout/install/format)

---

## Итоговый вердикт

# **FIX PLAN READY**

Происхождение ошибок установлено. Большинство блокеров CI **уже были на BASE**. RELEASE 3 добавил ограниченный набор новых проблем форматирования/типов и **улучшил** Prettier (302 → 74), но не сделал CI зелёным.

---

## 0. Метод и версии инструментов

| | |
|---|---|
| BASE snapshot | `git archive --format=zip` → `%TEMP%\ringoo-r7-base-clean` (не в working tree) |
| Инструменты | из текущего `backend/venv` + `frontend/node_modules` (**без** новых install) |
| Black | 26.1.0 |
| isort | 7.0.0 |
| flake8 | 7.3.0 |
| mypy | 1.19.1 (как в R6) |
| Prettier | 3.8.1 |
| Node | текущий PATH (тот же, что R6) |

**Конфиги без diff BASE→HEAD:** `backend/.flake8`, `backend/pyproject.toml` (black/isort/mypy), `frontend/package.json`, `frontend/eslint.config.*`, `frontend/vitest.config.ts`, prettier rc.

---

## 1. Backend — результаты

| Проверка | Команда | BASE exit | HEAD exit | Метрика BASE | Метрика HEAD |
|---|---|---:|---:|---|---|
| Black | `black --check .` | 1 | 1 | **173** would reformat | **190** would reformat |
| isort | `isort --check-only .` | 1 | 1 | config crash THIRDPARTY/`sentry_sdk` | **то же** |
| flake8 | `flake8 . --count --statistics` | 1 | 1 | `.flake8` `#` in ignore | **то же** |
| mypy | `mypy . --config-file=pyproject.toml` | 1 | 1 | **159** errors / 46 files | **167** errors / 49 files |

### Black происхождение

| | Count |
|---|---:|
| Fail на BASE | 173 |
| Fail на HEAD | 190 |
| Новые fail-файлы (есть на HEAD, нет на BASE) | ~47 (часть — untracked `zero_smoke` / tmp / scripts вне коммитов) |
| Из них в `b3a9db4..HEAD` tracked RELEASE | **21** |
| Исчезнувшие fail (были на BASE, нет на HEAD) | ~29 |

**Вывод:** массовый Black fail — **предсуществующий**. RELEASE добавил ~21 новых неотформатированных tracked файла (в основном новые tests/onec + lifecycle/reporting/benchmark).

### isort / flake8

Одинаковый **config crash** на BASE и HEAD. Diff конфигов пуст → **100% предсуществующие** проблемы окружения/конфига относительно текущих версий flake8 7.x / isort 7.x.

### mypy происхождение

| | |
|---|---|
| BASE | 159 errors / 46 files |
| HEAD | 167 errors / 49 files |
| Δ | **+8 errors**, **+3 files** |

**Новые файлы с ошибками (внесены RELEASE):**

| File | Errors | Причина (типы) |
|---|---:|---|
| `apps/products/services/lifecycle.py` | 3 | `no-any-return` (bool / ProductDeleteDecision) |
| `integrations/onec/reporting.py` | 2 | `unreachable` |
| `scripts/b8_018_load_benchmark.py` | 3 | `no-any-return` |

Остальные ~159 ошибок — **старые** (settings, users/views, tests payments, …).

---

## 2. Frontend — результаты

| Проверка | Команда | BASE | HEAD | Вывод |
|---|---|---|---|---|
| Prettier | `prettier --check 'src/**/*.{ts,tsx,…}'` | exit 1, **302** files | exit 1, **74** files | CI всё ещё красный; **улучшение −228** |
| ESLint | `eslint` / `npm run lint` | exit 0, **107** warnings | exit 0, **119** warnings | warnings **не** валят CI lint |
| TypeScript | `tsc --noEmit` | exit **0** | exit **0** | OK оба |
| Coverage | `vitest run --coverage` | exit 1 — fn **24.92%**, br **23.44%** | exit 1 — fn **25.74%**, br **26.95%** | порог 30% **не достигнут**; failure **pre-existing** |

### Prettier происхождение

| | Count |
|---|---:|
| Fail BASE | 302 |
| Fail HEAD | 74 |
| Исправлено с BASE (больше не fail) | **~251** |
| Новые fail только на HEAD | **22** (почти все — новые файлы RELEASE 3) |
| Fail HEAD ∩ файлы RELEASE 3 | **37** (22 новых + 15 изменённых, уже «грязных» или оставшихся) |

**Новые Prettier-проблемы RELEASE (примеры):**  
`auth-refresh.ts`, `checkout-idempotency.ts`, `public-site-routes.ts`, `AdminQueryError.tsx`, `*.test.ts(x)` Fix packs, `responsive-contracts.test.ts`.

**Вывод:** Prettier на remote BASE уже был красным сильнее; RELEASE частично отформатировал дерево правками, но оставил/добавил 74 fail, из них 22 чисто новые.

### Coverage

Пороги в `vitest.config.ts` (**lines/functions/branches: 30**) **не менялись**.  
BASE уже не проходил functions/branches. HEAD чуть лучше, но всё ещё &lt; 30%.  
→ падение `npm run test:coverage` в CI — **предсуществующее**, не регрессия порогов.

---

## 3. Матрица происхождения (BLOCK 5)

| Проверка | BASE | HEAD | Новые проблемы | Старые проблемы | Вывод |
|---|---|---|---|---|---|
| Black | 173 fail files | 190 fail files | ~21 tracked в RELEASE | ~150+ уже на BASE | Предсуществующий долг + точечные новые |
| isort | config FAIL | config FAIL | 0 | config | Чинить конфиг (не код RELEASE) |
| flake8 | config FAIL | config FAIL | 0 | `.flake8` comments | Чинить `.flake8` |
| mypy | 159/46 | 167/49 | +8 в 3 новых файлах | 159 | Точечно lifecycle/reporting/benchmark; bulk — отдельно |
| Prettier | 302 | 74 | 22 новых файла | 52 из 74 уже/остаток | Сначала format 22–37 RELEASE; bulk — опционально |
| Coverage | FAIL &lt;30% | FAIL &lt;30% | нет (даже чуть лучше) | thresholds | Политика CI / тесты — Группа C |
| ESLint | 107 warn | 119 warn | ~12 warn | 107 | Не блокер CI `npm run lint` |
| tsc | PASS | PASS | — | — | OK |

---

## 4. План исправлений (BLOCK 6)

### Группа A — Обязательные точечные (без смены бизнес-логики)

1. **`.flake8`:** убрать inline `# …` из списка `ignore` (только коды) — разблокирует flake8 на BASE и HEAD.  
2. **`[tool.isort]`:** добавить корректные `sections` / `known_third_party` (или убрать конфликт THIRDPARTY) — разблокирует isort.  
3. **Black** на **21** новых/изменённых RELEASE py-файлах (список в `backend/var/r7/black_new_files.txt` ∩ git range).  
4. **Prettier** на **22** новых frontend-файлах RELEASE (+ желательно остальные 15 из 37 в range).  
5. **mypy** точечно: `lifecycle.py`, `reporting.py`, `b8_018_load_benchmark.py` (типизация/`cast`/unreachable) — либо временно не включать scripts в mypy paths (осознанное решение → C).

### Группа B — Предсуществующие

1. Black: остальные ~150+ файлов с BASE.  
2. mypy: 159 старых ошибок.  
3. Prettier: 52 из 74 HEAD fails вне «чисто новых» (многие были в BASE).  
4. Coverage &lt; 30% уже на BASE.

### Группа C — Архитектурные / политические решения

1. Снизить или сузить `vitest` coverage thresholds / `include` — **только после** явного ACK (сейчас порог формально не выполнялся и на BASE).  
2. Массовый `black` + Prettier всего репо.  
3. mypy overrides / exclude `scripts/`, settings.  
4. CI: сделать lint jobs non-blocking — не рекомендуется без обсуждения.

---

## 5. Минимальный fix-план к «зелёному» CI (рекомендация)

**Фаза 1 (разблок конфигов):** A1 + A2.  
**Фаза 2 (долг RELEASE):** A3 + A4 (+ A5 по желанию).  
**Фаза 3:** решение по coverage (C1) **или** добор тестов до 30%.  
**Фаза 4 (опционально):** B mass format / mypy cleanup.

После фаз 1–2 + C1 (или реальный coverage) — повторить RELEASE 6 smoke.

---

## 6. Ограничения / непроверенное

- CI Postgres/Redis pytest **не** сравнивался (как в R6).  
- `npm audit` / Next build на BASE не дублировались (R6 HEAD: PASS).  
- Сравнение Prettier/ESLint использует **текущие** Prettier 3.8.1 / ESLint из HEAD `node_modules` на дереве BASE (версии пакетов BASE lock не переустанавливались — допустимо, т.к. `package.json` без diff).  
- Untracked `b8_018_zero_smoke.py` может попадать в локальный Black HEAD scan (не в 9 коммитах).  
- Временный junction `node_modules` только в `%TEMP%\…\frontend` для coverage BASE.

---

## 7. Контроль неизменности рабочей копии

| Проверка | Результат |
|---|---|
| Branch | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| Status | тот же exclude/HOLD/R3–R6 set (+ этот R7 report после записи) |
| Исходники / lockfiles | не менялись |
| Коммиты | не создавались |

Артефакты диагностики: `backend/var/r7/*`, `%TEMP%\ringoo-r7-base-clean` — не для commit.

---

## Остановка

Исправления / format / commit / push / fetch / migrate / APPLY — **не выполнялись**.  
Можно переходить к отдельному этапу исправлений по Группам A→C после вашего подтверждения.
