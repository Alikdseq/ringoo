# FIX-PACK C — Bearer refresh, session hint и устойчивость сессии (B8-002, B8-006, B8-020)

**Дата:** 2026-11-14  
**Среда:** локально `C:\ringoo`  
**Git branch / HEAD до работ:** `main` / `b3a9db4`  
**Production:** не затрагивался  
**Коммит:** не создавался  
**Backend модели / migrate:** не менялись  

---

## 1–3. Исходные описания из BLOCK 8

| ID | Критичность | Описание из BLOCK 8 | Файлы | Воспроизведение |
|---|---|---|---|---|
| **B8-002** | Critical (Bearer) / Low (cookie prod) | Refresh axios **всегда** шлёт `X-Auth-Cookies: 1`; backend (`jwt_cookies.client_uses_cookie_auth`) strip'ает `access`/`refresh` из JSON → в Bearer-режиме сессия ломается | `lib/api/client.ts` ↔ `jwt_cookies.py` | `NEXT_PUBLIC_USE_AUTH_COOKIES=0`, 401→refresh |
| **B8-006** | High | Неуспешный cookie refresh не чистит session hint → UI «как будто вошёл» | `client.ts` / `auth-mode.ts` | Просроченная cookie-сессия |
| **B8-020** | High | `setAuthSessionHint` в `login()` до завершения MFA | `auth.service.ts` `login()`, `admin/login/page.tsx` | Admin login с MFA |

Рекомендации аудитора: не слать header в Bearer; clear hint на fail refresh; hint только после MFA.

---

## 4. READ-ONLY результаты

### Подтверждение

| ID | Подтверждён? | Причина | Мин. исправление | Риск |
|---|---|---|---|---|
| B8-002 | **Да** | Dedicated refresh instance всегда ставил `X-Auth-Cookies: 1` (строка ~101 старого `client.ts`) | Header только если `authCookiesMode()` | Низкий для cookie-prod; критичен для Bearer |
| B8-006 | **Да** | В `.catch` cookie refresh вызывался только `clearAuthTokens()`, без `clearAuthSessionHint` | Clear tokens+hint+notify | Средний UX/security perception |
| B8-020 | **Да** | `login()` в cookie-mode всегда `setAuthSessionHint` до проверки `admin_mfa_required` | Hint после MFA / если MFA не нужен | Средний (admin UX) |

### Уже OK (не переписывали)

- Single-flight (`isRefreshing` + shared promise) — был, сохранён.
- Interceptor refresh только на **401**, не на **403**.
- Refresh через отдельный axios (не через `apiClient` interceptors).
- Guest cart `withCredentials` / FIX-PACK A guest token — независимы от JWT refresh.
- FIX-PACK B cancel FSM — не затрагивался.

### Вне scope (не чинили)

- HttpOnly cookie может выставляться backend при login до MFA (флаг `ringoo_session`) — отдельный hardening.
- Полный E2E ЮKassa return в браузере.

---

## 5–6. Архитектура до / после

**До:** refresh logic внутри `client.ts`; Bearer refresh слал cookie header; fail refresh не чистил hint; login ставил hint до MFA.

**После:**

```
auth-refresh.ts  — single-flight refreshAccessToken + invalidatePendingAuthRefresh
client.ts        — interceptors 401→refresh (один retry), 403 без refresh
auth.service.ts  — login/MFA hint; logout → invalidatePendingAuthRefresh
auth-mode.ts     — notifyAuthSessionChanged (общий)
```

Backend JWT endpoints **не менялись**.

---

## 7–8. Что исправлено / файлы

| Файл | Изменение |
|---|---|
| `frontend/src/lib/api/auth-refresh.ts` | **новый** — refresh + epoch invalidate |
| `frontend/src/lib/api/client.ts` | тонкий client; re-export refresh; 401-only retry |
| `frontend/src/lib/api/services/auth.service.ts` | B8-020 login/MFA; logout invalidate |
| `frontend/src/lib/auth-mode.ts` | `notifyAuthSessionChanged` |
| `frontend/src/lib/api/auth-refresh.test.ts` | **новый** |
| `frontend/src/lib/api/services/auth.login-mfa.test.ts` | **новый** |
| `docs/audit/FIX_PACK_C_AUTH_REFRESH_REPORT.md` | отчёт |

---

## 9–13. Поведение после фикса

### Refresh
- Cookie mode: `POST /auth/token/refresh/` + `X-Auth-Cookies: 1`, body `{}`, результат `""`.
- Bearer mode: body `{ refresh }`, **без** `X-Auth-Cookies`; сохраняет access/refresh из JSON.
- Пустой `access` в ответе → clear session (защита от strip).

### Параллельные 401
- Один in-flight `refreshPromise`; ожидающие получают тот же результат.

### Неудачный refresh
- `clearAuthTokens` + `clearAuthSessionHint` + `ringoo-auth` event.
- Нет бесконечного retry (`_retry` один раз).

### Session hint
- Cookie login без MFA → set hint.
- Cookie login с `admin_mfa_required` → **не** set / clear hint.
- `verifyAdminMfa` → set hint.
- Hint ≠ доказательство JWT; `/auth/me` по-прежнему серверный.

### Logout
- `invalidatePendingAuthRefresh()` до/вместе с clear → in-flight refresh не восстановит токены.

---

## 14. FIX-PACK A

- Guest success path / `guest_access_token` / public `/orders/success` — FE unit tests зелёные; JWT refresh не использует guest token.
- Backend `test_fix_pack_a_guest_success` + SEC-006: **passed**.

## 15. FIX-PACK B

- `test_fix_pack_b_order_cancellation` + SEC-006: **passed**. Код cancel/FSM не менялся.

## 16. Оплата и корзина

- Код payments/cart не менялся.
- `apiClient.withCredentials` сохранён (guest session cart).
- ЮKassa return по-прежнему через `guest_token` в sessionStorage (не JWT).

---

## 17. Запущенные проверки (факт)

| Команда / набор | Результат |
|---|---|
| vitest `auth-refresh` + `auth.login-mfa` | **9 passed** |
| vitest + Fix-pack A success/path tests | **17 passed** |
| `tsc --noEmit` | **exit 0** |
| eslint изменённых FE файлов | **exit 0** |
| `npm run build` | **exit 0** |
| pytest Fix A + Fix B + SEC-006 | **28 passed** |
| `manage.py check` | OK |
| `makemigrations --check` | No changes |

Backend unit JWT suite не расширялся (backend не менялся).

---

## 18. Известные ограничения

- Cookie `ringoo_session` от backend после login+MFA-required может ещё существовать до logout — hint больше не ставится, но полный cookie wipe до MFA — вне этого pack.
- Interceptor guest GET retry после failed refresh — прежнее поведение для публичных GET.
- Browser E2E параллельных 401 / MFA admin — не гонялись вручную.

---

## 19. BLOCK 8 вне этого Fix-pack

B8-004, B8-005, B8-007, B8-008, B8-009, B8-011… — без изменений.  
B8-001/B8-003 — Fix-pack A. B8-010 — Fix-pack B.

---

## 20. Production

Production не открывался; APPLY/migrate/restart/платежи/`.env`/commit — нет.

---

## Вердикт

**FIX-PACK C принят к проверке:** B8-002, B8-006, B8-020 подтверждены и исправлены; тесты и build зелёные; Fix-pack A/B не регрессировали.

**Следующий Fix-pack самостоятельно не начат.**
