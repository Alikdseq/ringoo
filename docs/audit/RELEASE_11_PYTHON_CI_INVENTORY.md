# RELEASE 11 — Полная инвентаризация Python CI

**Дата:** 2026-11-16  
**Проект:** `C:\ringoo`  
**Основание:** R6 BLOCKED → R7 FIX PLAN → R8 config PASS WITH WARNINGS → R9 Black PASS → R10 isort inventory PASS  
**Вердикт:** **PASS**

READ-ONLY. Исходники и конфигурации не изменялись. Артефакты: `backend/var/r11/`, этот отчёт.

---

## 1. Branch / HEAD

| | |
|---|---|
| Branch | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| BASE | `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8` |

Dirty tree (ожидаемо, не трогалось): R8 configs (3) + R9 Black (21) + пользовательские untracked/HOLD.

---

## 2. Версии инструментов (локально)

| Tool | Version |
|---|---|
| Python | 3.11.9 |
| Black | **26.1.0** |
| isort | **7.0.0** |
| flake8 | **7.3.0** (pycodestyle 2.14.0, pyflakes 3.4.0, mccabe 0.7.0) |
| mypy | **1.19.1** |

`requirements-dev.txt`: `black>=23.12.1`, `isort>=5.13.2`, `flake8>=7.0.0`, `mypy>=1.7.1` (нижние границы).

---

## 3. Точные CI-команды vs pre-commit

### GitHub Actions — `.github/workflows/backend-ci.yml` (блокирующие lint-шаги)

Рабочая директория: `./backend`. После `pip install -r requirements-dev.txt` дополнительно: `pip install black isort flake8 mypy` (**без pin версий**).

| Step | Команда | Блокирует job `lint` |
|---|---|---|
| Black | `black --check --diff .` | Да |
| isort | `isort --check-only --diff .` | Да |
| Flake8 | `flake8 . --count --statistics` | Да |
| MyPy | `mypy . --config-file=pyproject.toml` | Да |

Дополнительно (вне scope этого аудита форматирования, но тоже CI):

- job `test`: migrate + `pytest --cov=...` (PG15/Redis)
- job `security`: bandit + `pip-audit --fail-on=high`

### Pre-commit (локально; **не** заменяет GHA)

| Hook | Pin | Отличие от CI |
|---|---|---|
| black | **23.12.1** | CI/локальный venv ≈ 26.x |
| isort | **5.13.2** + `--profile=black` | CI/venv = **7.0.0**; R8-конфиг критичен для 7.x |
| flake8 | **7.0.0** + `--extend-ignore=E203,W503` + flake8-docstrings | CI читает `backend/.flake8`; args hook ≠ полный `.flake8` |
| mypy | **v1.7.1** + `--ignore-missing-imports --no-strict-optional` | CI: `pyproject.toml` / mypy **1.19.x** |

**Вывод:** ориентир для «зелёного CI» — команды GHA + конфиги в `backend/`, не pins pre-commit.

### Конфиги (R8 сохранены, не менялись в R11)

- `backend/.flake8` — ignore без inline `#`
- `backend/.isort.cfg` + `[tool.isort]` — `THIRDPARTY`, `sentry_sdk`, skip venv
- `backend/pyproject.toml` — black/isort/mypy

---

## 4. Black — актуальные результаты

Команда: `python -m black --check --diff .`  
Артефакты: `var/r11/black_diff.txt`, `black_stderr.txt`, `black_fail_files.txt`

| Метрика | Значение |
|---|---:|
| Would reformat (текущее WT) | **170** |
| Unchanged | 168 |
| Exit | 1 |
| R9 (21 файл) сейчас pass | **21 / 21** |
| Tracked remaining | **167** |
| tmp/untracked в fails | 3–4 |

### Сравнение с BASE (R7 black lists)

| | Count |
|---|---:|
| BASE fails (R7) | ~173–174 |
| HEAD fails до R9 (R7) | ~190 |
| После R9 (сейчас) | **170** |
| Пересечение со старым BASE-долгом | **144** |
| Tracked «новые» vs BASE fail-set (не из R9) | **22** (в основном mgmt commands / drills вне RELEASE range) |

**RELEASE 1–3:** 21 файл R9 исправлены и проходят. Остальные ~32 RELEASE-touched py всё ещё в black-fails — это файлы, которые **уже** были плохими на BASE (изменены в RELEASE, но не входили в «new fails» R7∩range).

---

## 5. isort — актуальные результаты

Команда: `python -m isort --check-only --diff .` (конфиг R8)  
Артефакты: `var/r11/isort_*.txt` + опора на R10.

| Метрика | Значение |
|---|---:|
| Fails (WT) | **116** |
| Group A RELEASE ∩ fails | **33** |
| Group B other tracked | **81** |
| Group C tmp | **2** |
| New vs BASE (fixed config) | **~11** |
| Old (уже на BASE) | **~105** |

### Риск-корзины (среди isort fails)

| Корзина | Примеры / count |
|---|---|
| После `django.setup()` | `scripts_sentry_smoke.py`, `scripts/b8_018_load_benchmark.py`, test_*.py smoke helpers (~7) |
| Celery / settings / urls | `config/celery.py`, `config/settings/base.py`, `config/urls.py`, `config/api_urls.py` |
| Signals | `apps/bonus/signals.py` |
| Локальные импорты | `apps/orders/views.py`, `integrations/onec/importer.py`, часть tests |
| TYPE_CHECKING | не выделены отдельно в текущем fail-set |
| HOLD | `b8_018_zero_smoke.py` — вне плана |

Детальная разбивка AUTO/MANUAL: `docs/audit/RELEASE_10_ISORT_INVENTORY.md`.

---

## 6. flake8 — актуальные результаты

Команда: `python -m flake8 . --count --statistics`  
Конфиг загружается (**нет** `ValueError: Error code '#'`).  
Артефакты: `var/r11/flake8_out.txt`, `flake8_findings.json`, `flake8_by_code.txt`

| Метрика | Значение |
|---|---:|
| Findings | **242** |
| Files | **55** (tracked ~51) |
| RELEASE files with findings | **16** / **42** findings |
| BASE (temp tree + R8 `.flake8`) | **192** findings / ~47 files |
| Δ CUR−BASE | **+50** findings / +8 files |

### По кодам (текущее)

| Count | Code | Класс |
|---:|---|---|
| 56 | C901 | сложность |
| 41 | W293 | стиль (whitespace blank line) |
| 37 | E402 | import не наверху (часто после setup/django) |
| 29 | E111 | стиль indent |
| 23 | E121 | стиль continuation |
| 18 | E225 | стиль operators |
| 10 | F841 | unused local |
| 7 | E231 | стиль |
| ≤5 | E226, W291, W391, E401, … | стиль |
| 1 | F811 | возможный баг (redefinition) |
| 1 | F541 | f-string без placeholder |

### Категории (агрегат)

| Категория | Count |
|---|---:|
| Форматирование/стиль (E1xx/E2xx/E3xx/W29x/W39x/E401/E701) | ~137 |
| E402 (порядок импортов / late import) | 37 |
| Сложность C901 | 56 |
| Unused F841 | 10 |
| Потенциальные ошибки (F811, F541) | 2 |

### RELEASE flake8 hotspots

| File | Findings |
|---|---:|
| `scripts/b8_018_load_benchmark.py` | 8 |
| `tests/test_int004_int005_yookassa_refund_metadata.py` | 6 |
| `integrations/onec/orders.py` | 5 |
| `integrations/onec/parser.py` | 4 |
| `integrations/onec/importer.py` / `apps/orders/views.py` / `b8_018_rerun_dryrun.py` | 3 each |
| … | ≤2 |

Новые vs BASE files: `import_onec_catalog.py`, `stock_ops.py`, `b8_018_*`, plus tmp/var/HOLD (вне CI-цели tracked).

**Не** добавлялись ignore-коды.

---

## 7. mypy — актуальные результаты

Команда: `python -m mypy . --config-file=pyproject.toml`  
Артефакты: `var/r11/mypy_out.txt`, `mypy_findings.json`, `mypy_by_code.txt`

| Метрика | Значение |
|---|---:|
| Errors | **167** |
| Files | **49** |
| Checked | 338 source files |
| R7 BASE | 159 / 46 files |
| R7 HEAD / сейчас | 167 / 49 files |
| Δ | **+8 errors**, **+3 files** |

### По типам (сейчас)

| Count | Code |
|---:|---|
| 115 | `no-any-return` |
| 10 | `used-before-def` |
| 9 | `unreachable` |
| 8 | `assignment` |
| 6 | `var-annotated` |
| 5 | `dict-item` |
| 4 | `attr-defined` |
| 4 | `arg-type` |
| 3 | `index` |
| 2 | `misc` |
| 1 | `call-overload` |

### Новые файлы RELEASE (R7 → подтверждено R11)

| File | Errors | Codes |
|---|---:|---|
| `apps/products/services/lifecycle.py` | 3 | `no-any-return` |
| `integrations/onec/reporting.py` | 2 | `unreachable` |
| `scripts/b8_018_load_benchmark.py` | 3 | `no-any-return` |

### По слоям (грубо)

| Слой | Error lines |
|---|---:|
| Бизнес/apps/integrations/config | ~158 |
| Tests | ~2 |
| Scripts | ~6 |

Рекомендуемые безопасные фиксы (план, не выполнение): явные `bool(...)` / `cast` / сужение типов; для `unreachable` — пересмотр ветвлений без `# type: ignore` и без ослабления mypy config.

---

## 8. Сводка BASE vs HEAD / WT

| Tool | BASE | HEAD/WT сейчас | Примечание |
|---|---:|---:|---|
| Black | ~173–174 | **170** (после R9) | R9 снял 21; долг ≈ BASE |
| isort | 105 (fixed cfg) | **116** | конфиг R8 обязателен |
| flake8 | 192 (fixed cfg) | **242** | до R8 был config crash |
| mypy | 159 | **167** | +3 файла RELEASE |

---

## 9. Новые нарушения RELEASE 1–3 (фокус)

| Tool | Что нового / осталось от RELEASE |
|---|---|
| Black | R9 закрыл 21 new-fail; другие RELEASE-touched остаются в общем долге BASE |
| isort | ~9–11 new vs BASE; Group A = 33 файлов в диапазоне |
| flake8 | +8 files / часть +50 findings (scripts b8_018, stock_ops, import_onec_catalog, …) |
| mypy | **+8** на `lifecycle.py`, `reporting.py`, `b8_018_load_benchmark.py` |

---

## 10. Старый технический долг

- Black: **~144–167** tracked файлов вне R9  
- isort: **~105** файлов уже на BASE  
- flake8: **~192** findings на BASE  
- mypy: **~159** errors / 46 files на BASE (доминирует `no-any-return`)

Цель следующих этапов — **полный green** соответствующих GHA lint-шагов, не «уменьшить на N».

---

## 11. Риски и чувствительные файлы

| Область | Файлы | Риск |
|---|---|---|
| Celery | `config/celery.py` | autodiscover / import order |
| Django settings/urls | `config/settings/base.py`, `urls.py`, `api_urls.py` | side-effect imports |
| Signals | `apps/bonus/signals.py` | регистрация при import |
| Local imports | `apps/orders/views.py`, `integrations/onec/importer.py` | циклы |
| setup() scripts | `scripts_sentry_smoke.py`, `b8_018_load_benchmark.py` | E402 + isort + mypy |
| Payments/cart/FSM | orders/cart/payments views & tests | регрессии checkout |
| HOLD | `b8_018_zero_smoke.py` | не включать |
| tmp/var diagnostics | `tmp/yk_*`, `var/r10/collect_*` | не целевой CI tracked scope; шумят локально |

---

## 12. План исправлений (следующие RELEASE — по согласованию)

Принцип: **отдельные узкие этапы**, не один массовый патч. После каждого этапа: соответствующий `--check` + Django check + точечные тесты затронутых модулей.

### Этап A — Black (остаток долга)

| | |
|---|---|
| Scope | **167** tracked remaining (`var/r11/black_tracked_remaining.txt`); **исключить** уже зелёные 21 R9 |
| Группы | 6 батчей ≈30 файлов (apps → integrations → tests → scripts) |
| Зависимости | Нет (можно первым) |
| Проверка | `black --check` на батче, затем полный `black --check .` |
| Риски | Низкие (форматирование); не смешивать с isort в одном коммите |

### Этап B — isort

| | |
|---|---|
| Scope | 116 fails → сначала Group A (33), затем B |
| Подгруппы | (B1) AUTO blank/alpha ~22 из R10; (B2) AUTO_LIKELY; (B3) MANUAL: celery/signals/settings/local/setup |
| Зависимости | Желательно после Black на тех же файлах (меньше churn) |
| Проверка | `isort --check-only` + import-smoke / точечные pytest |
| Риски | Средние–высокие на B3 |

### Этап C — flake8

| | |
|---|---|
| Scope | 242 findings / 55 files |
| Подгруппы | (C1) стиль W/E whitespace & indent; (C2) F841/F541; (C3) E402 совместно с isort; (C4) C901 — осмысленный рефакторинг или точечное снижение сложности; (C5) F811 |
| Зависимости | После Black/isort (часть E/W уйдёт) |
| Проверка | `flake8 . --count --statistics` → 0 |
| Риски | C901 может затронуть логику — отдельные PR; **не** расширять ignore |

### Этап D — mypy

| | |
|---|---|
| Scope | 167 errors / 49 files |
| Подгруппы | (D1) 8 новых RELEASE (`lifecycle`, `reporting`, `b8_018_load_benchmark`); (D2) бизнес apps/integrations; (D3) settings/tests/scripts |
| Зависимости | После стабилизации формата (A/B); не блокируется flake8 строго |
| Проверка | `mypy . --config-file=pyproject.toml` → 0 |
| Риски | Ложные «упрощения» типов; **запрет** массовых `type: ignore` / ослабления pyproject |

### Очерёдность (рекомендуемая)

```text
A Black batches → B isort (safe→manual) → C flake8 residual → D mypy
```

Каждый инструмент — отдельные согласованные RELEASE/PR. Цель: все четыре GHA lint-команды exit 0.

---

## 13. Регрессионные проверки (R11)

| Проверка | Результат |
|---|---|
| `git diff --check` | PASS |
| `manage.py check` (`config.settings.test`) | PASS |
| `makemigrations --check --dry-run` | PASS |

Тесты с пользовательской БД / APPLY / production — не запускались.

---

## 14. Git status

Без изменений от R11 в исходниках/конфигах. Добавлены только:

- `docs/audit/RELEASE_11_PYTHON_CI_INVENTORY.md`
- `backend/var/r11/*` (диагностика)

HEAD: `fcc23d001ddea397e152adde4ea4c86f25ff74e3` · branch `main` · **без коммитов**.

---

## Вердикт

**PASS** — актуальный аудит Black/isort/flake8/mypy выполнен после R8–R10, CI-команды зафиксированы, BASE/HEAD сопоставлены где достоверно, план устранения долга разбит на узкие этапы.

**Остановка.** Исправления не начинать без отдельного согласования следующего RELEASE.  
**Никаких коммитов и push.**
