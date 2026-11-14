# FIX-PACK F — AdminGuard / доступ к административным маршрутам (B8-009)

**Дата:** 2026-11-14  
**Среда:** локально `C:\ringoo`  
**Git branch / HEAD до работ:** `main` / `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8`  
**Production:** не затрагивался  
**Коммит / push:** не создавались  
**`.env` / секреты / JWT / cookie values:** не читались и не выводились  

---

## 1. Что обнаружено до изменений (READ-ONLY)

### Исходный B8-009 (BLOCK 8)

| Поле | Значение |
|---|---|
| Severity | High |
| Суть | `AdminGuard` только client-side; нет middleware RBAC; при прямом URL возможна «мелькающая» админ-оболочка |
| Рекомендация | Ок если API enforce; усилить UX gate |

### Фактическое состояние AdminGuard

Файл: `frontend/src/components/admin/AdminGuard.tsx` (через `ShellSelector` на всех `/admin/*`).

| Состояние | Было |
|---|---|
| Loading auth | Spinner |
| Unauthenticated | Spinner + redirect `/admin/login` |
| Staff loading | Spinner (children не рендерились — мерцание **контента страницы** уже блокировалось) |
| Forbidden (403) | `fetchStaffAccess` глотал 403 → `null` → Spinner + **redirect на `/`** |
| 401 staff-access | То же → redirect `/` (а не login) |
| 5xx / сеть | `throw` → `staffError` → Spinner + **redirect на `/`** (ошибочно как «гость») |
| Staff OK | `AdminLayout` + children |
| Login page | children без layout |

Проблемы Fix F:

1. Нет явной **403-страницы** — только редирект домой под видом loading.  
2. **5xx/сеть** трактовались как отказ в доступе (редирект home), без retry.  
3. `fetchStaffAccess` возвращал `null` на 401/403 — AdminGuard не различал статусы.  
4. Middleware RBAC отсутствует; `proxy.ts` в cookie-режиме проверяет лишь **наличие** JWT-cookie (не staff).

### Backend RBAC (проверено)

- `GET /api/v1/auth/staff-access/` — `IsAuthenticated`; non-staff → **403**; MFA claim при OTP.  
- Admin API: `admin_permissions(group)` = `IsAuthenticated + IsStaff + AdminMfaVerified + HasAdminGroup`.  
- Тесты: `test_admin_api_auth.py`, `test_admin_integrity.py`, `TestUserMeAndStaffAccess` — non-staff **403** на `/admin/products/` и staff-access.

**Вывод F-02:** доказанных дыр в RBAC admin API нет → **backend не менялся**.

### Middleware / proxy

`frontend/src/proxy.ts`:

- Cookie mode: `/admin` без cookie → redirect login (UX only).  
- Bearer mode: **нет** cookie-gate (токены в storage).  
- Staff/группы **не** проверяются на edge.

**Почему middleware RBAC не добавляли (F-03):** нельзя безопасно проверить staff на сервере Next без дублирования JWT-логики и без доверия к client hints; Bearer-режим невидим для cookie-check. Backend остаётся единственным источником истины; мерцание закрывается AdminGuard shell.

---

## 2. Таблица сценариев (аудит → решение)

| Сценарий | Было | Риск | Решение Fix F |
|---|---|---|---|
| Гость `/admin/products` | login redirect | Низкий | Сохранено |
| Auth без staff | Spinner → `/` | UX | **403 UI**, без AdminLayout |
| Staff OK | Layout | — | Без изменений контракта |
| staff-access 401 | Spinner → `/` | Сессия | Redirect **`/admin/login`** |
| staff-access 403 | Spinner → `/` | UX | Forbidden page |
| staff-access 500 | Spinner → `/` | Ложный «гость» | Unavailable + **Повторить** |
| Сеть недоступна | как 5xx | То же | Unavailable + retry |
| Прямая ссылка `/admin/*` | Spinner до staff | Мелькание layout | Neutral shell до settle |
| Refresh внутри admin | refetch | — | staleTime 60s; при ошибке — gate |
| Сессия истекла | interceptor + null | — | 401 → login |
| API без staff | 403 | — | Уже enforce; без правок BE |
| Staff с группой | 200 | — | Сохранено |

---

## 3. Что исправлено

### F-01 AdminGuard

- Пока staff-access не settled — только нейтральный shell (без `AdminLayout` / children).  
- Unauthenticated / 401 → `/admin/login?next=…`.  
- 403 / non-staff → страница «Доступ запрещён» (не home под spinner).  
- 5xx/сеть → «Не удалось проверить доступ» + retry; **не** redirect на `/`.  
- Login page без staff query.  
- Нет бесконечного loading при завершившейся ошибке.

### `fetchStaffAccess`

Больше не глотает 401/403 в `null` — ошибки пробрасываются. `checkStaffAccess` ловит и возвращает `false`. Login обрабатывает throw.

### F-02 Backend

Не менялся.

### F-03 Middleware

Не добавлялся (см. обоснование выше). Существующий cookie presence check в `proxy.ts` не выдаётся за RBAC.

---

## 4. Изменённые файлы

| Файл | Изменение |
|---|---|
| `frontend/src/components/admin/AdminGuard.tsx` | Gate states F-01 |
| `frontend/src/components/admin/AdminGuard.test.tsx` | **новый** |
| `frontend/src/lib/api/services/auth.service.ts` | `fetchStaffAccess` throws |
| `frontend/src/lib/api/services/auth.staff-access.test.ts` | **новый** |
| `frontend/src/app/admin/login/page.tsx` | обработка throw staff-access |
| `docs/audit/FIX_PACK_F_ADMIN_GUARD_REPORT.md` | этот отчёт |

---

## 5. Тесты — фактические результаты

### Frontend

| Suite | Result |
|---|---|
| `AdminGuard.test.tsx` (8) | **passed** |
| `auth.staff-access.test.ts` (3) | **passed** |
| Fix C `auth-refresh.test.ts` | **passed** |
| Fix E `AdminQueryError` + logout-cart | **passed** |
| Итого прогон | **20 passed** |
| `tsc --noEmit` | **OK** |
| ESLint изменённых файлов | **OK** (`--max-warnings 0`) |
| `npm run build` | **OK** (exit 0) |

### Backend (без изменений кода)

| Suite | Result |
|---|---|
| `TestUserMeAndStaffAccess` | **passed** |
| `tests/test_admin_api_auth.py` | **passed** (5) |
| `tests/test_admin_integrity.py` + MFA (в широком прогоне) | admin RBAC **passed** |
| `manage.py check` | OK |
| `apps/users/tests.py::TestJwtLoginMergesGuestCart` | **failed** (stock «Товара нет в наличии») — **вне scope F**, не регрессия AdminGuard |

---

## 6. Влияние на Fix A–E и BLOCK 1–7

| Область | Влияние |
|---|---|
| Fix A/B/D | Нет (guest/orders/checkout не трогались) |
| Fix C | `logout` по-прежнему `removeQueries(staff-access)`; refresh не менялся; тесты refresh green |
| Fix E | `AdminQueryError` на detail pages совместим; AdminGuard не подменяет page-level 404 |
| BLOCK 1–7 / 1С / склад | Не менялись |

---

## 7. Непроверенное

1. Браузерный E2E: визуальное отсутствие flash AdminLayout (покрыто unit: loading без `admin-layout`).  
2. Полный MFA enrollment UI path при 403 `admin_mfa_required` (текст 403 через `getFriendlyErrorMessage`).  
3. Production cookie names / edge proxy parity.  

---

## 8. Критерии приёмки (самооценка)

| Критерий | Статус |
|---|---|
| Нет admin content до staff settle | Готов |
| Unauth → login | Готов |
| Non-staff → 403 UI | Готов |
| 5xx → retry, не guest | Готов |
| Backend RBAC без ослабления | Готов (без правок) |
| Middleware не выдаётся за RBAC | Отказались осознанно |
| Отчёт | Этот файл |

**СТОП:** Fix-pack F завершён. Следующий pack не начинался.
