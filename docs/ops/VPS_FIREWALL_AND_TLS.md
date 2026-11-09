# VPS firewall & TLS — Ringoo

## Целевая схема

```
Internet → :80/:443 (Caddy/Nginx on host)
         → 127.0.0.1:3000 frontend (Docker publish)
         → 127.0.0.1:8000 backend (optional; prefer Next proxy → web:8000)
Docker network: web ↔ db ↔ redis ↔ celery (no public DB/Redis ports)
```

Production Compose публикует web/frontend **только на 127.0.0.1** (`BACKEND_PUBLISH` / `FRONTEND_PUBLISH`).

## Firewall (пример ufw)

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status
```

Не открывать 5432, 6379, 8000, 3000 наружу.

## TLS

Примеры для **ringoo15.store**:

- `docs/ops/caddy.ringoo15.store.caddyfile` (канон)
- `docs/ops/caddy.production.example.caddyfile`
- `docs/ops/nginx.production.example.conf`

DNS перед TLS:

```text
A     ringoo15.store      → <VPS_IP>
A     www.ringoo15.store  → <VPS_IP>
```

Caddy автоматически получает сертификат Let’s Encrypt при корректном DNS.

Проверка после установки:

```bash
curl -I https://ringoo15.store
echo | openssl s_client -connect ringoo15.store:443 -servername ringoo15.store 2>/dev/null | openssl x509 -noout -dates
```

## Django proxy trust

В `.env.production`:

```text
TRUST_PROXY=1
AXES_IPWARE_PROXY_COUNT=1
SECURE_SSL_REDIRECT=True
```

Proxy должен **перезаписывать** `X-Forwarded-Proto` (не принимать клиентский заголовок as-is с WAN).
Backend слушает только localhost / Docker network.

## Статус

| Пункт | Статус |
|-------|--------|
| Примеры конфигов в репо | подготовлено |
| Firewall на реальном VPS | **NOT VERIFIED** |
| Живой TLS | **NOT VERIFIED** |
