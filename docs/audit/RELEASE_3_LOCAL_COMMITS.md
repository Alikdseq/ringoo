# RELEASE 3 — Локальные Git-коммиты

**Дата:** 2026-11-14  
**Branch:** `main`  
**Push / pull / fetch / migrate / APPLY / production:** **не выполнялись**

---

## 1. HEAD

| | SHA |
|---|---|
| Исходный | `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8` |
| Конечный | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |

---

## 2. Девять коммитов (порядок снизу вверх = 1→9)

| # | SHA | Message | Files |
|---|---|---|---:|
| 1 | `765caf9aecab7cec4ca0ac1c188a0f8f9f91eb18` | `feat(onec): implement full stock snapshot synchronization` | 42 |
| 2 | `8c7a1def15d4bda03ef38fe7f8ba8bd586c964e8` | `fix(orders): align order transitions and stock release` | 12 |
| 3 | `127ad21558dba715df9d152c84cac0fc66b5e8e7` | `fix(checkout): harden guest checkout and idempotency` | 19 |
| 4 | `5c779e993cdeebebe17ebb65d97314cd1e3206b2` | `fix(auth): stabilize token refresh and session handling` | 9 |
| 5 | `f2386f7127568d0feb72da930bf8aa3421cbea81` | `fix(admin): handle staff authorization states correctly` | 11 |
| 6 | `2eaa1a12ee52f2ac0a3ae66613faa439d5a7b41e` | `fix(frontend): improve storefront responsive behavior` | 15 |
| 7 | `05d8a223f24e63786418e87d6794b131ff159e4c` | `feat(seo): add sitemap and robots configuration` | 5 |
| 8 | `5488db803c756b1f20f6f8d2d9d374a24085c1e0` | `docs(audit): add release and integration audit reports` | 24 |
| 9 | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `test(onec): add isolated import benchmark tooling` | 2 |

Сумма файлов в коммитах: 42+12+19+9+11+15+5+24+2 = **139**.

---

## 3. Этап 0

| Проверка | Результат |
|---|---|
| Branch `main` | OK |
| HEAD до коммитов = `b3a9db4…` | OK |
| Status согласован с манифестом (+ RELEASE_2_1) | OK |
| `zero_smoke` исключён из C9 | OK |
| Trailing whitespace `docs/API.md` 257–259 | **исправлено** перед C8 |
| `git diff --check` после фикса API.md | clean (до stage docs) |

---

## 4. Контроль по коммитам

| Commit | Staged count | `diff --cached --check` | Notes |
|---|---:|---|---|
| 1 | 42 | clean | миграции 0008/0009 включены |
| 2 | 12 | clean | после C1 |
| 3 | 19 | clean | BE+FE вместе |
| 4 | 9 | clean | |
| 5 | 11 | clean | после C4 |
| 6 | 15 | clean | |
| 7 | 5 | clean | |
| 8 | 24 | **warn: markdown hard-break trailing spaces** в audit MD | состав OK; массовый trim **не** делался (разрешён только API.md) |
| 9 | 2 | clean | без `zero_smoke` |

---

## 5. Оставшиеся незакоммиченные файлы

| Path | Reason |
|---|---|
| `промпт.txt` (M) | Exclude |
| `Описание работ.txt` (??) | Exclude |
| `docs/Инструкция_API_1С_для_разработчиков_сайта.docx` | Exclude |
| `docs/Интеграция с 1С — объём работ.docx` | Exclude |
| `docs/Онлайн-оплата — объём работ.docx` | Exclude |
| `docs/Отчёт_интеграции_Ringo_1С_Сбер_касса.docx` | Exclude |
| `frontend/AGENTS.md` | Exclude |
| `backend/scripts/b8_018_zero_smoke.py` | HOLD (RELEASE 2.1) |
| `docs/audit/RELEASE_3_LOCAL_COMMITS.md` | этот отчёт (создан после коммитов) |

`backend/var/` — ignored, не в status.

---

## 6. Проверки исключений в истории

Поиск по `b3a9db4..HEAD` имён: `zero_smoke`, `промпт`, `Описание`, `.docx`, `AGENTS.md`, `.env`, `backend/var` — **совпадений нет**.

---

## 7. Подтверждения

- **Push не выполнялся.**  
- Deploy / migrate / 1С APPLY / benchmark run — не выполнялись.  
- Ветка не переключалась.  
- `git add .` / `git add -A` не использовались.

---

## Остановка

Локальные коммиты готовы. Дальнейший push — только по отдельному подтверждению.
