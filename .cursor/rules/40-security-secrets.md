---
description: "Безопасность: секреты, JWT/cookies, CORS/CSRF"
globs:
  - "backend/**/*.py"
  - "frontend/**/*.{ts,tsx}"
  - "**/*.env*"
---

## Безопасность

### Секреты

- Никогда не добавляй секреты в git (особенно `.env`, ключи платежей, SECRET_KEY, токены).
- На фронтенде любые `NEXT_PUBLIC_*` переменные **публичные**. Нельзя класть туда приватные ключи.

### Auth режимы (важно)

- В проекте допускаются 2 режима:
  - **Bearer (local storage)** — токен в `Authorization`.
  - **HttpOnly cookies** — токен в cookies (`NEXT_PUBLIC_USE_AUTH_COOKIES`).
- Любая правка auth обязана сохранять:
  - refresh на 401 в `apiClient`;
  - корректность CORS/credentials для гостевой корзины.

### CORS/CSRF

- Если фронт и бэк на разных origin — учитывай `withCredentials` и CORS заголовки.
- Не добавляй “разрешить всё” в prod; в dev допускается шире, но не переносить на production.

