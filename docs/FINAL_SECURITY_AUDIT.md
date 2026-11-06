# FINAL SECURITY AUDIT — Ringoo (02.11.2026, post-validation)

Домен целевого демо: **https://ringoo15.store**

Режим: FINAL VALIDATION. Commit / push / deploy / prod migrate / реальные платежи — **не выполнялись**.

## Git baseline

| Поле | Значение |
|------|----------|
| Branch | `main` |
| HEAD | `8a0bd5f` |
| Staged | empty |
| Пользовательские UI-правки | сохранены |

## Проверки (этой сессии)

| Проверка | Результат | Статус |
|----------|-----------|--------|
| Backend pytest | **131 passed**, 6 skipped | **VERIFIED** |
| Admin MFA tests | **11 passed** (forge claim / refresh / blacklist) | **VERIFIED** |
| Frontend Vitest | **80 passed**, 0 failed (31 files) | **VERIFIED** |
| Type-check | `tsc --noEmit` exit 0 | **VERIFIED** |
| ESLint | см. прогон сессии (warnings допустимы) | **PARTIAL** / см. вывод |
| Backend Docker image | `ringoo-web:prod-test`, user `django` | **VERIFIED** |
| Frontend Docker image | `ringoo-frontend:prod-test`, user `nextjs`, build args ringoo15.store, ONLINE_PAYMENT=0 | **VERIFIED** |
| Frontend container smoke | `HTTP 200` на `127.0.0.1:13000/` | **VERIFIED** |
| Compose prod merge | DB/Redis ports None; web/frontend `127.0.0.1`; нет `.env.development` | **VERIFIED** |
| `check --deploy` (Linux image) | exit 0 + spectacular/HSTS warnings | **VERIFIED** |
| MFA enroll конкретного admin | — | **NOT VERIFIED** (VPS manual) |
| Live TLS / firewall / DNS | — | **NOT VERIFIED** (VPS) |
| Offsite backup | docs/scripts only | **NOT VERIFIED** |

## Vitest — что было сломано и как закрыто

| Тест | Причина | Тип | Исправление |
|------|---------|-----|-------------|
| cart/page.test | `@/` alias + import после `vi.mock` → resolve fail | test env | alias в `vitest.config.ts`; mock без re-import |
| checkout/page.test | не хватало mocks auth/stores; `/Шаг 1/` multiple | test | mocks + `getAllByText` |
| orders/* page tests | async/mock/next navigation conflicts | test | стабильные mocks + QueryClient retry:false |
| jsdom 28 undici | invalid onError | test env | pin `jsdom@26` |

## MFA (независимая проверка)

- Password JWT **не** содержит `admin_mfa`.
- Admin API / staff-access требуют claim при `ADMIN_OTP_ENABLED`.
- `/auth/mfa/verify/` выдаёт claim только после TOTP.
- Refresh **сохраняет** claim только если он уже был; без claim не выдаёт.
- Повторный refresh после rotate+blacklist → отказ.
- Body `admin_mfa:1` **не** обходит TOTP.
- Enrollment на VPS — ручной (`docs/ops/ADMIN_MFA_SETUP.md`).

## Payments (demo)

- UI: `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED=0` в Dockerfile ARG (build-time).
- Backend: `payments_disabled` если `SBER_ECOM_ENABLED=false`.
- Sber / 1С / касса OFF в `.env.production.example`.

## READY FOR VPS — REMAINING MANUAL ACTIONS

Полная последовательность для **ringoo15.store**:  
→ `docs/FINAL_DEPLOYMENT_CHECKLIST.md` (раздел READY FOR VPS).

Кратко: DNS → ufw 80/443 → `.env.production` → compose up → role/migrate → MFA enroll → Caddy (`docs/ops/caddy.ringoo15.store.caddyfile`) → smoke HTTPS → backup.

## Вердикт

**READY FOR VPS DEPLOYMENT**

Код, тесты и Docker-образы проверены локально под демо `ringoo15.store`.  
**READY FOR PUBLIC ACCESS** — только после ручных шагов на VPS (firewall, TLS, MFA enroll, DB grants, smoke HTTPS).
