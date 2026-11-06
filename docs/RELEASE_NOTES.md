# Release notes — public demo prep (2026-11-02)

## Security / ops

- Production Compose: web/frontend bind to `127.0.0.1` only; DB/Redis unpublished.
- Admin MFA: TOTP required for Admin API + Next admin (`admin_mfa` JWT claim).
- Online payment UI flag wired in Dockerfile (default OFF); backend refuses pay when Sber disabled.
- Docs/scripts: Postgres least privilege, encrypted backup (age), VPS firewall/TLS, MFA setup.

## Integrations (demo)

Sber / ЮKassa / 1С / online fiscal — **OFF**. Checkout: cash / card_on_delivery / bank_transfer.

## Not done on VPS yet

Firewall, live TLS, MFA enroll, DB GRANTs, offsite backup, HTTPS smoke.
