# Чеклист соответствия 152-ФЗ / практике РКН (Ringoo)

Ориентир: [проверки РКН на сайтах](https://habr.com/ru/articles/1029636/). Использовать на staging перед продакшеном и после изменений юридических текстов.

| # | Проверка | Ожидание | Где смотреть |
|---|----------|----------|-------------|
| 1 | Отдельные галочки, не отмечены по умолчанию | Register: ПДн, оферта, маркетинг (opt); Checkout, CRM, футер | `/register`, `/checkout`, форма «Не нашли товар», футер |
| 2 | Submit без обязательных галочек | Ошибка / кнопка disabled | UI + API 400 |
| 3 | Политика ПДн полная | Оператор, цели, Метрика, cookie, права, РФ | `/docs/privacy` |
| 4 | Отдельный текст согласия на ПДн | Ссылка из галочек | `/docs/consent` |
| 5 | Маркетинг отдельным документом | Ссылка из opt-in галочки | `/docs/marketing-consent` |
| 6 | Cookie / Метрика в документах | Описание cookie и отказ | `/docs/cookies` |
| 7 | Метрика не грузится до «Принять» | Нет `mc.yandex.ru` в Network до согласия | DevTools → Network |
| 8 | Баннер cookie | «Принять» / «Только необходимые» | Первый визит (инкогнито) |
| 9 | Реквизиты не заглушки | ИНН/ОГРН из env на prod | `/docs/requisites`, `NEXT_PUBLIC_ORG_*` |
| 10 | Нет «продолжая пользоваться…» | Нет подразумеваемого согласия | `/docs/privacy` |
| 11 | Логи согласий | ConsentRecord в Django admin | `/admin/` → Записи согласий |
| 12 | Уведомление в реестре РКН | Тексты сайта = уведомление | `docs/RKN_OPERATOR_REGISTRATION.md` |
| 13 | Фото сотрудников | Дисклеймер под блоком менеджеров | `/about#managers` |
| 14 | `POLICY_VERSION` | Одинаково backend/frontend | `POLICY_VERSION`, `NEXT_PUBLIC_POLICY_VERSION` |

## Smoke (ручной)

1. Регистрация без каждой обязательной галочки → не проходит.
2. Заказ без согласия на ПДн → не проходит.
3. CRM без `consent_personal_data` → 400.
4. Принять cookie → появляется запрос к `/api/v1/legal/analytics-consent/`, в DOM — скрипт Метрики (если задан `NEXT_PUBLIC_YANDEX_METRICA_ID`).
5. «Только необходимые» → Метрика не подключается.

## Автотесты

- Backend: `apps.users.tests`, `apps.users.tests_legal`, `apps.crm.tests`
- Frontend: `YandexMetrika.test.tsx`, `analytics-consent.test.ts`, `checkout/page.test.tsx`
