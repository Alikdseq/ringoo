# Чек-лист запросов внешним сторонам

Чтобы после ответов сразу перейти к живым испытаниям. Код фаз A/B готов на моках; реальные POST — только после пунктов ниже.

## Сбербанк / Support ecom

- [ ] Тестовый логин `*-api` и пароль
- [ ] Подтверждение: callback только ЛК / достаточно `dynamicCallbackUrl`
- [ ] Есть ли checksum/token для callback на договоре
- [ ] Требования TLS / сертификат НУЦ для ecomtest
- [ ] Разрешены ли `reverse.do` / `refund.do` с API-логина теста
- [ ] Будет ли фискализация через шлюз (`orderBundle`) на договоре
- [ ] Тестовые карты и сценарии успеха/отказа

Готово на нашей стороне: клиент, register/status/callback/reverse/refund API, runbook — `docs/integrations/sber-staging-runbook.md`.  
Преflight без банка: `python manage.py check_sber_staging`.

## Специалист 1С (Алан)

- [x] Метод создания/оплаты заказа: `POST SiteOrders/orders` (`paid` false→true)
- [x] Отмена: `POST SiteOrders/orders/cancel`
- [x] Регистрация: `ClientId` (не `partnerId`)
- [x] Публикация: `/razrab/hs/` (единая база каталог+клиенты+заказы)
- [ ] Подтвердить полный URL тестовой публикации (хост)
- [ ] UUID склада для доставки → `ONE_C_DEFAULT_WAREHOUSE_ID`
- [ ] Сетевой доступ backend → тестовая база
- [ ] Сменить пароль API, светившийся в инструкции; выдать новый только в секреты сервера
- [ ] Явное ОК на тестовые POST регистрации и заказов

Готово на нашей стороне: каталог, регистрация, SiteOrders sync/cancel, серии в Stock/OrderItem, Celery hooks, mock-тесты.  
Контракт: `docs/integrations/1c-api-contract.md`.

## Владелец / бухгалтер / касса

- [ ] Схема: чек через Сбер **или** отдельный провайдер
- [ ] Касса/ОФД (АТОЛ / Эвотор / …)
- [ ] СНО, ставка НДС, признак расчёта
- [ ] Политика late payment: `manual` / `revive` / `reverse` → `LATE_ONLINE_PAYMENT_POLICY`
- [ ] Когда переводить наличные/при получении в `paid=true` в 1С

Готово на нашей стороне: политика late payment в коде; фискализация **не** реализована (отдельный этап).
