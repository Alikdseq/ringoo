# Полный технический аудит готовности: Сбер + 1С + онлайн-касса

**Дата:** 25 октября 2026
**Режим:** только аудит (код не менялся, миграции на живые БД не применялись, внешние API не вызывались)
**Критерий:** готовность к интеграционному тестированию и последующему production без фундаментальной переработки архитектуры

---

## 1. Краткий вывод о готовности

| Компонент | Готовность | Вердикт |
| --- | --- | --- |
| **Сбербанк ecom (MVP оплата)** | ~90% к тест-контуру (код) | Фаза A в коде: register/status вне txn, expire+bank check, late-pay, reverse/refund client, reconcile, throttle, retry UX, env/runbook. **Не подтверждено на реальном шлюзе.** Блокеры: доступы `*-api`, HTTPS callback, migrate на staging. |
| **1С каталог + партнёр** | ~60% к тест-контуру | Парсер/импорт/клиент/регистрация партнёра есть (моки). **Заказы в 1С — нет.** Живой API 1С не вызывался. |
| **1С заказы** | 0% (+ stub) | Placeholder `integrations/onec/orders.py`; нужен контракт специалиста 1С. |
| **Онлайн-касса / фискализация** | 0% (+ stub) | Placeholder `integrations/fiscal`; схема не выбрана. |
| **Сквозной процесс оплата→чек→1С** | Не готов | Цепочка обрывается после подтверждения оплаты. |
| **Инфраструктура** | Готова в репо | `.env.example`, beat expire+reconcile, `monitor_hung_payments`; staging migrate — ops. |

**Главный вывод:** фундаментально переписывать архитектуру заказов/корзины/оплаты **не нужно**. Для интеграционных тестов Сбера достаточно доступов + небольшой доработки безопасности/операционки. Для 1С-заказов и кассы — сначала решения и контракты от внешних сторон, затем код.

---

## 2. Факты аудита

### 2.1. Сбербанк

| Факт | Доказательство |
| --- | --- |
| Клиент ecom JSON: `register.do`, `getOrderStatusExtended.do` | `backend/integrations/sber/client.py` |
| База по умолчанию тест: `https://ecomtest.sberbank.ru` | settings + client |
| Бой в доке: `https://epay.sberbank.ru` (не `securepayments`) | `docs/integrations/sber-acquiring.md`, ecom.yaml |
| Модель `Payment` + unique paid-per-order | `backend/apps/payments/models.py` |
| Сумма только из `Order.total_amount` | `initiate_sber_payment` |
| Callback → всегда сверка API | `handle_sber_callback` → `sync_payment_from_bank` |
| Таймаут неоплаченных + снятие резерва | `expire_unpaid_online_orders`, Celery beat 5 мин |
| Frontend: checkout → formUrl → return poll | `checkout/page.tsx`, `payment/return/page.tsx` |
| Нет `refund.do` / `reverse.do` | grep по backend |
| Нет checksum callback (в OpenAPI не подтверждён) | `SberCallbackView` docstring |
| HTTP register **внутри** `@transaction.atomic` | `services.py` — риск orphan-платежа в банке при сбое БД после register |
| Оплата после cancel → payment failed + log, без auto-refund | `sync_payment_from_bank` |
| Документ `AUDIT_INTEGRATION_1C_SBER_KASSA.md` **устарел** (пишет «нет эквайринга») | §8 vs текущий код |

### 2.2. 1С

| Факт | Доказательство |
| --- | --- |
| Реализовано: folders, products, SiteRegistration | `integrations/onec/client.py`, STAGE2 |
| Placeholder путей заказов без методов | `OneCEndpoints.orders_create/status` |
| `User.onec_partner_id` есть; на signup не вызывается | models + флаг `ONE_C_SYNC_PARTNER_ON_REGISTER` без wiring |
| У Order/OrderItem нет `onec_*` | `orders/models.py` |
| Excel и 1С-импорт сосуществуют без lock | `bulk_import` vs `importer` |

### 2.3. Касса

| Факт | Доказательство |
| --- | --- |
| Нет orderBundle в register | `SberEcomClient.register_order` |
| Нет моделей Receipt/Fiscal | apps/payments |
| OrderItem без НДС/СНО/paymentObject | models |
| Сбер поддерживает АТОЛ/Эвотор/Бизнес.ру/OFD.RU при настройке мерчанта | официальная дока / ecom.yaml |

### 2.4. Тесты (фактический запуск)

```text
python manage.py test tests.test_sber_payments tests.test_onec_catalog tests.test_onec_http \
  --settings=config.settings.test -v1
→ Ran 42 tests in 0.438s — OK
```

Только моки. **Реальный шлюз Сбера и сервер 1С не проверялись.**

---

## 3. Таблица проблем по приоритету

| P | Проблема | Компонент | Критичность |
| --- | --- | --- | --- |
| P0 | Нет тестовых доступов Сбера (`*-api`) | Сбер | Блокирует реальные тесты |
| P0 | Нет метода создания заказа в 1С | 1С | Блокирует обмен заказами |
| P0 | Не выбрана схема кассы / не подключена ККТ | Касса | Блокирует легальные онлайн-расчёты (после юр. оценки) |
| P1 | `register` внутри DB-транзакции | Сбер | Риск рассинхрона банк/БД |
| P1 | Оплата после expire/cancel без reverse/refund | Сбер | Деньги у мерчанта, заказ отменён |
| P1 | Expire не сверяет статус в банке перед отменой | Сбер | Усиливает P1 |
| P1 | Миграция `payments.0001` не в git history / не применена на staging | Infra | Блокирует деплой оплаты |
| P1 | SBER/ONE_C нет в `.env.example` / GITHUB_SECRETS | Infra | Ошибки конфигурации |
| P2 | Нет checksum/IP allowlist callback | Сбер | Смягчено re-query API |
| P2 | Нет scoped throttle на pay/callback | Infra | Abuse / лимиты банка |
| P2 | Нет мониторинга зависших pending/paid-after-cancel | Ops | Операционный риск |
| P2 | Fail page без «Оплатить снова» | Frontend | UX |
| P2 | Нет refund API для админки | Сбер | Блокирует возвраты в продукте |
| P2 | Excel vs 1С без политики владельца карточки | 1С | Расхождения каталога |
| P3 | Устаревший AUDIT_INTEGRATION_… | Docs | Путаница |
| P3 | `ONE_C_SYNC_PARTNER_ON_REGISTER` не подключён | 1С | Можно отложить |
| P3 | Статус шлюза 3 пишется как failed, не reversed | Сбер | Косметика/учёт |

---

## 4. Сквозные сценарии и риски

| # | Сценарий | Сейчас | Риск | Ожидаемо | Доработка |
| --- | --- | --- | --- | --- | --- |
| 1 | Успех: заказ→оплата→чек→1С | Оплата до `confirmed`; чек/1С нет | Неполный бизнес-процесс | После paid: чек, затем 1С | Касса + order API 1С |
| 2 | Не завершил оплату | Expire → cancel + release | OK для MVP | То же + опц. decline в банке | Опционально |
| 3 | Оплата есть, callback нет | Return poll / GET payment sync | OK если пользователь вернулся | Плюс периодический reconcile | Задача reconcile pending |
| 4 | Callback много раз | Идемпотентный sync | Низкий | То же | — |
| 5 | Банк оплатил, Ringo down | Callback 200 даже при sync fail; нет outbox | Потеря статуса до ручной сверки | Очередь retry / reconcile по sber_order_id | P1 |
| 6 | Оплата ОК, касса fail | Кассы нет | Нет чека | Retry чека, не дублировать | После выбора кассы |
| 7 | Оплата ОК, 1С down | 1С заказов нет | Заказ только на сайте | Outbox + retry + ручной replay | После API 1С |
| 8 | Timeout cancel, потом оплата | Payment failed + error log | Деньги без заказа | reverse/refund или восстановление заказа | P1 |
| 9 | Возврат клиенту | Нет API | Только ЛК банка | `refund.do` + статус | P2 |
| 10 | Два pay одновременно | select_for_update + reuse form | Низкий | То же | Тест concurrency |
| 11 | Смена суммы после Payment | Сумма фиксируется в Payment; mismatch → failed | Защита есть | Запрет изменения order amount после register | Явная политика |
| 12 | Повтор 1С/чека после сети | Нет отправки | — | Идемпотентный external id | После интеграций |

**Бизнес-решения, которые ещё не зафиксированы кодом:** момент передачи в 1С (только после paid?), момент чека (сразу при register vs после deposited), политика late payment (refund vs revive order).

---

## 5. Вопросы внешним специалистам

### Сбербанк / Support ecom

1. Подтвердить логин `*-api`, пароль, merchantLogin (если есть).
2. Callback URL: куда регистрировать — только ЛК или достаточно `dynamicCallbackUrl`?
3. Есть ли checksum/token для callback на вашем договоре?
4. Нужен ли сертификат НУЦ Минцифры на сервере сайта для ecomtest/epay?
5. Будет ли фискализация через шлюз (orderBundle) на этом договоре?
6. Разрешены ли refund/reverse с API-логина теста?

### Специалист 1С

1. Метод и путь создания заказа сайта (не выдумывать `SiteOrders/*`).
2. Формат тела, обязательные поля, `partnerId`.
3. Позиции: `code`, qty, цена (чья?).
4. Внешний id сайта и защита от дублей.
5. Ответ успеха и способ статуса.
6. Когда создавать документ: до/после оплаты.
7. Склад/серия при сетевом резерве.
8. Сверка XML HTTP vs файловые выгрузки.
9. Доступ backend → UT11 (VPN/HTTPS).

### Владелец / бухгалтер / касса

1. Схема: чек через Сбер **или** отдельный провайдер?
2. Касса: АТОЛ / Эвотор / Бизнес.ру / OFD.RU / иное?
3. СНО, ставка НДС, признак расчёта (полный / предоплата).
4. Email/phone обязательны для чека — политика для гостей без email.
5. Маркировка товаров — нужна ли?

---

## 6. Необходимые доступы и настройки

| Что | Зачем |
| --- | --- |
| `SBER_ECOM_USERNAME` / `PASSWORD` (тест) | register/status |
| `SBER_ECOM_ENABLED=true` только на staging | Включение клиента |
| Публичный HTTPS URL → `/api/v1/payments/sber/callback/` | Callback |
| `SBER_ECOM_RETURN_URL` / `FAIL_URL` или `FRONTEND_URL` | Возврат с ПШ |
| Применение миграции `payments` | Таблица Payment |
| Celery worker + beat (или cron expire) | Таймауты |
| ONE_C_* + сеть до UT11 | Каталог/партнёр на живом API |
| Договор/учётки кассы + настройка в СберБизнес (если сценарий A) | Чеки |
| Боевые логины Сбера | Только после успешных тестов + ваше подтверждение |

Секреты в репозитории **не найдены** (кроме тестовой строки `"secret"` в unit-тестах).

---

## 7. Пошаговый план исправлений (на согласование)

**Код не начинать до вашего «ок».**

### Фаза A — готовность к тест-контуру Сбера (без кассы/1С-заказов)

**Статус кода (после доработки):** пункты 1, 3–7 закрыты в репозитории. Пункт 2 (migrate на живом staging) — операция деплоя, см. runbook.

1. [x] SBER/ONE_C/ONLINE_*/LATE_* в `.env.example` + [`integrations/sber-staging-runbook.md`](./integrations/sber-staging-runbook.md).
2. [ ] Применить `migrate payments` на staging (ops). Миграция `0001_initial` в репо.
3. [x] HTTP `register`/`status` вне долгой DB-транзакции; `reconcile_open_payments` + Celery beat.
4. [x] Перед expire — сверка с банком; при paid — не cancel.
5. [x] Paid-after-cancel → `needs_review` + `LATE_ONLINE_PAYMENT_POLICY` (manual/revive/reverse).
6. [x] Throttle pay/callback; кнопка «Оплатить снова» на fail.
7. [x] Баннер устаревания в `AUDIT_INTEGRATION_1C_SBER_KASSA.md`.

### Фаза B — после ответов 1С

8. Реализовать order push по **подтверждённому** контракту; outbox; только после `Payment.paid` (если так решите).
9. Поля `Order.onec_*`, snapshot `onec_code` в OrderItem; идемпотентный external id.

### Фаза C — после выбора кассы

10. Сценарий A: orderBundle + настройки мерчанта в банке; или B: отдельный кассовый клиент.
11. Модель FiscalReceipt, идемпотентность, retry, связь с Payment/Order.
12. Поля НДС/СНО на товар/заказ по данным бухгалтера.

### Фаза D — production gate

13. Smoke на тесте → заявка на боевые логины.
14. Переключение `SBER_ECOM_BASE_URL` на `epay` **только по вашему явному подтверждению**.
15. Мониторинг pending > N мин, failed callbacks, paid-after-cancel.

---

## 8. Чек-листы

### A. Готовность к интеграционному тестированию (локально / моки)

- [x] Unit-тесты Сбер + 1С каталог (моки; без внешнего шлюза)
- [x] Dry-run импорт 1С из XML-файлов
- [x] Код pay/status/callback/expire + reconcile + late-pay + throttle + retry UX
- [x] `.env.example` с переменными + runbook
- [ ] Staging с migrate payments
- [ ] Публичный HTTPS для callback (ngrok/staging)
- [ ] Тестовые карты из доки Сбера после выдачи доступа

### B. Готовность к реальным тестам (нужны внешние стороны)

- [ ] Логин/пароль Сбер `*-api` + ЛК operator
- [ ] Callback зарегистрирован, return/fail URL белые
- [ ] Доступ backend → ecomtest (TLS, НУЦ при требовании)
- [ ] (Опц.) ONE_C доступы + VPN к UT11
- [ ] Решение по кассе **не обязательно** для теста только оплаты

### C. Готовность к production

- [ ] Успешные тесты на ecomtest (успех/отказ/повтор callback/timeout)
- [ ] Refund/reverse или документированный процесс через ЛК
- [ ] Политика late payment согласована и реализована
- [ ] Касса подключена и чек проверен (если обязателен для схемы)
- [ ] Заказы в 1С после оплаты (если требуется бизнесу)
- [ ] Beat/cron expire в prod
- [ ] Мониторинг и runbook инцидентов
- [ ] **Явное подтверждение** на переключение epay

---

## 9. Что нельзя подтвердить без внешних доступов

1. Успешный `register.do` / `formUrl` на ecomtest.
2. Реальные статусы и callback delivery.
3. Соответствие живого XML 1С файловым выгрузкам.
4. Создание партнёра/заказа на реальной UT11.
5. Формирование чека АТОЛ/Эвотор/… через шлюз.
6. Поведение НУЦ-сертификата в вашем runtime.
7. Лимиты и особенности конкретного merchantLogin.
8. Юридическая обязательность онлайн-кассы для вашей схемы — только юрист/бухгалтер.

---

## Зависимости ролей

| Кто | Действия |
| --- | --- |
| **Вы** | Согласовать план фаз A–D; выдать/запросить доступы; выбрать кассу и момент передачи в 1С; подтвердить бой |
| **Сбер** | Тестовые/боевые логины; callback; опц. фискализация на договоре |
| **Специалист 1С** | Контракт заказа; тестовая база; сеть |
| **Кассовый провайдер / бухгалтер** | ККТ, ОФД, СНО, НДС |
| **Разработка (после согласования)** | Фаза A сразу; B/C после внешних ответов |

---

**Фаза A в коде выполнена.** Дальше: доступы Сбера + migrate на staging → реальные тесты оплаты; параллельно — ответы по чек-листу [`integrations/EXTERNAL_REQUESTS_CHECKLIST.md`](./integrations/EXTERNAL_REQUESTS_CHECKLIST.md) для фаз B/C.

Бизнес-решения до prod: 1С только после оплаты?; касса через Сбер или отдельно?; `LATE_ONLINE_PAYMENT_POLICY`.
