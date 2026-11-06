---
description: "Frontend: Next.js/TypeScript/TanStack Query конвенции Ringoo"
globs:
  - "frontend/**/*.ts"
  - "frontend/**/*.tsx"
---

## Frontend (Next.js + TS + TanStack Query)

### API слой

- Все сетевые запросы — через `frontend/src/lib/api/client.ts` и `frontend/src/lib/api/services/*.ts`.
- Не делай `fetch` напрямую в компонентах, если уже есть service/hook.
- Ошибки в UI выводи через `getFriendlyErrorMessage` (единый тон и локализация).

### TanStack Query (серверное состояние)

- Query keys — стабильные и предсказуемые (массивы). Используй константы ключей там, где важно (`CART_QUERY_KEY`, `AUTH_ME_QUERY_KEY`).
- После мутаций обязательно делай **инвалидацию релевантных ключей** (пример: заказ → `['cart']`, `['orders']`).
- Избегай лишних запросов:
  - не инвалидируй без нужды, если уже делаешь `setQueryData` и данные полностью актуальны;
  - используй `enabled` для условных запросов (auth-зависимые страницы).

### Формы и UX

- На submit:
  - блокируй повторные нажатия (`disabled` + `loading`);
  - показывай ошибки валидации поля рядом с полем;
  - для сетевых ошибок — единый дружелюбный текст + (опционально) техническая причина в dev.
- Loading:
  - не допускай «белого экрана»; используй skeleton/placeholder.

### Типизация

- Не используй `unknown` для payload критичных мутаций (login/register/create order/cart).
- TypeScript типы должны отражать фактический контракт DRF.

