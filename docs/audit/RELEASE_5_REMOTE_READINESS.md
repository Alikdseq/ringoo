# RELEASE 5 — Проверка удалённого Git-репозитория перед Push

**Дата / время проверки:** 2026-11-14 16:12:50 +03:00  
**Проект:** `C:\ringoo`  
**Режим:** READ-ONLY (без fetch / push / pull / merge / rebase)  
**Основание:** RELEASE 4 = PASS WITH RISKS  

---

## 10. Итоговый вердикт

# **READY WITH CONDITIONS**

Remote `main` = `b3a9db4…` — **прямой предок** локального HEAD; локально **9** коммитов впереди, **0** позади; divergent history **нет**.  
Автоматического deploy в GitHub Actions **не найдено**.  

Push возможен после учёта условий §8–§9 (в первую очередь: backend lint CI, Prettier, возможный Vercel/GitHub protection).

**Не** присвоен `READY FOR PUSH` из‑за непроверенных обязательных CI-линтеров backend и неизвестных branch protection / внешнего auto-deploy.

---

## 1. Локальный Git

| Проверка | Результат |
|---|---|
| Branch | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` (= ожидаемый) |
| Upstream | `origin/main` |
| Log −9 | 9 коммитов RELEASE 3 на месте |
| Status | только exclude / HOLD / отчёты R3–R4 (не в 9 коммитах) |

### История RELEASE 3 (локально впереди remote)

1. `765caf9` feat(onec)…  
2. `8c7a1de` fix(orders)…  
3. `127ad21` fix(checkout)…  
4. `5c779e9` fix(auth)…  
5. `f2386f7` fix(admin)…  
6. `2eaa1a1` fix(frontend)…  
7. `05d8a22` feat(seo)…  
8. `5488db8` docs(audit)…  
9. `fcc23d0` test(onec)…  

Исключённые файлы (`zero_smoke`, docx, промпт, Описание, AGENTS, RELEASE_3/4) в диапазоне `b3a9db4..HEAD` — **отсутствуют**.

---

## 2. Remote configuration (без секретов)

| Поле | Значение |
|---|---|
| Remote name | `origin` |
| URL | `https://github.com/***` (credentials в URL не обнаружены; полный URL не печатается) |
| Fetch/push | оба → тот же origin |
| Другие remotes | нет |

---

## 3. Remote main SHA

| Поле | Значение |
|---|---|
| Команда | `git ls-remote --heads origin main` |
| Успех сети | **да** (exit 0) |
| Remote branch | только `main` (других heads на origin не видно) |
| SHA | `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8` |
| Subject (локальный объект) | `fix: align staff access cache shape for AdminGuard` |
| Локальный `origin/main` ref | совпадает с ls-remote (`b3a9db4…`) |

`git fetch` **не** выполнялся.

---

## 4. Сравнение историй

| Проверка | Результат |
|---|---|
| Remote object locally | **да** (`git cat-file -t` → `commit`) |
| `merge-base(HEAD, remote)` | `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8` |
| Remote is ancestor of HEAD | **да** (`merge-base --is-ancestor` exit 0) |
| Ahead | **9** |
| Behind | **0** |
| Divergent | **нет** |

Классификация: remote main **совпадает с базой** локальных 9 коммитов (RELEASE 3 стартовал с этого SHA); локальная ветка **строго впереди**.

---

## 5. CI configuration

Источник: локальные `.github/workflows/*` (GitLab CI отсутствует).

| Workflow | Триггер | Содержание | Auto-deploy? |
|---|---|---|---|
| `frontend-ci.yml` | push/PR → `main` (+ develop/staging), paths `frontend/**` | `npm ci`, `npm audit --omit=dev --audit-level=high`, **`npm run lint`** (= `eslint .`, **без** `--max-warnings 0`), `format:check`, `type-check`, `test:coverage`, `build` | нет |
| `backend-ci.yml` | push/PR → `main`, paths `backend/**` | black / isort / flake8 / mypy; **Postgres 15 + Redis**; `migrate`; pytest+cov; security job | нет (migrate только CI DB) |
| `pr-check.yml` | **только** `pull_request` | backend+frontend checks | нет |
| `container-trivy.yml` | push `main` при изменении Dockerfile/requirements | Trivy image scan | нет |
| `lighthouse-ci.yml` | schedule / manual | prod CWV | нет |
| `load-test-manual.yml` | `workflow_dispatch` | manual | нет |
| `dast-zap-baseline.yml` | `workflow_dispatch` | manual | нет |

### ESLint vs RELEASE 4

| Контекст | max-warnings | Риск от 119 warnings |
|---|---|---|
| GitHub `frontend-ci` `npm run lint` | **не задан** (default ESLint: warnings ≠ fail) | **низкий** для warnings-as-fail |
| Локальный QA R4 `eslint --max-warnings 0` | 0 | fail (не то же, что CI) |
| `.pre-commit-config.yaml` eslint hook | `--max-warnings=0` | только если pre-commit запускается локально |

**Дополнительный CI-риск frontend:** `npm run format:check` (Prettier) и `npm audit --audit-level=high` — в RELEASE 4 **не** прогонялись.

**Дополнительный CI-риск backend:** black / isort / flake8 / mypy на новых файлах — в RELEASE 4 **не** прогонялись (pytest+check только).

Postgres service в backend-ci: **да** → CI ближе к prod concurrency, чем локальный SQLite.

---

## 6. Automatic deployment

| Источник | Вывод |
|---|---|
| GitHub Actions workflows | **нет** job deploy/ssh/kubectl/vercel action на push |
| `vercel.json` | описывает services/rewrites; **не** доказывает auto-deploy |
| `docker-compose.prod.yml` | локальный/серверный compose, не CI trigger |
| GitHub Environments / Vercel Git integration / branch protection | **недоступны** без API/auth — **UNKNOWN** |

**Вывод:** из репозитория не следует автоматический production deploy при `git push origin main`. Внешний hook (Vercel/hosting) остаётся неизвестным.

---

## 7. Незакоммиченные файлы

| Path | В 9 коммитах? | Попадёт в `git push` уже созданных коммитов? |
|---|---|---|
| `промпт.txt` (M) | нет | **нет** (uncommitted) |
| `Описание работ.txt` | нет | **нет** |
| 4× `.docx` | нет | **нет** |
| `frontend/AGENTS.md` | нет | **нет** |
| `backend/scripts/b8_018_zero_smoke.py` | нет (HOLD) | **нет** |
| `docs/audit/RELEASE_3_LOCAL_COMMITS.md` | нет | **нет** |
| `docs/audit/RELEASE_4_FINAL_QA.md` | нет | **нет** |
| `docs/audit/RELEASE_5_REMOTE_READINESS.md` | нет | **нет** (этот файл) |

Обычный `git push` отправляет **только объекты уже созданных коммитов**. Untracked/modified working tree **не** уезжает, пока их не закоммитить.

---

## 8. Риски публикации

| # | Сценарий | Статус | Доказательство |
|---|---|---|---|
| 1 | Remote main = база локальных коммитов | **да** | ls-remote SHA = `b3a9db4` = merge-base |
| 2 | Remote отстаёт | **да (ожидаемо)** | ahead=9, behind=0 |
| 3 | Чужие коммиты на remote | **нет** | behind=0, ancestor clean |
| 4 | Divergent history | **нет** | merge-base = remote tip |
| 5 | CI fail из‑за ESLint warnings | **маловероятно в GH** | CI: `eslint .` без `--max-warnings 0`; риск выше у Prettier/audit |
| 6 | Auto deploy на push | **не найден в Actions**; внешний UNKNOWN | workflows без deploy jobs |
| 7 | Branch protection / required PR | **UNKNOWN** | нет доступа к GitHub settings API |
| 8 | Ancestry not verified | **нет** | object local + is-ancestor OK |

### Условия перед/сразу после push (для READY WITH CONDITIONS)

1. Ожидать падения **backend-ci** lint (black/isort/flake8/mypy), если стиль новых файлов не соответствует — локально не проверялось.  
2. Ожидать падения **frontend-ci** на `format:check` или `npm audit` — не проверялось в R4.  
3. Убедиться вне репо, что Vercel/hosting **не** катит production с `main` без approve.  
4. Учесть branch protection: возможен отказ прямого push → нужен PR.  
5. После успешного push: migrate `stores.0008`/`0009` на staging **отдельным** шагом (не часть push).

---

## 9. Что остаётся неизвестным

- GitHub branch protection / required checks / rulesets.  
- Фактический статус Vercel (или иного) Git auto-deploy.  
- Пройдут ли black/isort/flake8/mypy / Prettier / npm audit на CI.  
- Требуется ли PR вместо прямого push в `main`.  
- Состояние remote после чужих push между этой проверкой и вашим push (без нового `ls-remote`).

---

## Остановка

`git push` / `fetch` / `pull` / merge / rebase / deploy / migrate / APPLY — **не выполнялись**.  

Дождаться отдельного подтверждения на push (и при необходимости — на предварительный fetch, если remote изменится).
