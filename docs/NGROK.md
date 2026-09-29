# Ngrok — демо Ringoo (два URL: фронт + API)

Вариант **A**: один процесс ngrok, **два разных HTTPS-адреса** — сайт на `:3000` и API на `:8000`.  
Один и тот же домен на оба порта даёт **ERR_NGROK_334** — так делать нельзя.

## Предварительно

1. Аккаунт [ngrok](https://dashboard.ngrok.com/) и authtoken:
   ```powershell
   ngrok config add-authtoken <ВАШ_ТОКЕН>
   ```
2. Стек Ringoo слушает на хосте:
   - Frontend: `http://localhost:3000` (Docker: `docker compose up -d`)
   - Backend: `http://localhost:8000`

## Быстрый старт (Windows)

Из корня репозитория:

```powershell
# Рекомендуется: ngrok + production frontend (без HMR, стабильная главная)
.\scripts\ngrok\run-demo.ps1
```

Только туннель и env (dev без HMR WebSocket — см. `docker-compose.ngrok.yml`):

```powershell
.\scripts\ngrok\start-ringoo.ps1
```

Скрипт start-ringoo:

1. Завершает другие `ngrok.exe` (если не передан `-NoKill`).
2. Стартует `ringoo-frontend` + `ringoo-backend` из [scripts/ngrok/ngrok.ringoo.yml](../scripts/ngrok/ngrok.ringoo.yml).
3. Читает `http://127.0.0.1:4040/api/tunnels` и обновляет:
   - `frontend/.env.local` — `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_API_V1_URL`
   - `backend/.env.development` и `backend/.env` — `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` (**Docker читает `.env.development`**)

После смены env **пересоздайте** контейнеры (обычный `restart` **не** подхватывает новый `env_file`):

```powershell
docker compose up -d --force-recreate web frontend
```

Только синхронизация env (ngrok уже запущен):

```powershell
.\scripts\ngrok\sync-ngrok-env.ps1
```

## Конфиг туннелей

| Endpoint | Локально | Публичный URL |
|----------|----------|----------------|
| `ringoo-frontend` | `127.0.0.1:3000` | Зарезервированный: `demanding-most-caramel.ngrok-free.dev` (если привязан в dashboard) |
| `ringoo-backend` | `127.0.0.1:8000` | Только при `-Dual` (два URL; см. `ngrok.ringoo.dual.yml`) |

**По умолчанию один туннель** на `:3000` — Next.js проксирует `/api/v1` и `/media` на Django. Так нет ERR_NGROK_334 и ошибки sync «No tunnels».

Два туннеля: `powershell -File scripts\ngrok\start-ringoo.ps1 -Dual`

Файлы:

- `scripts/ngrok/ngrok.ringoo.yml` — ngrok **v3** (по умолчанию)
- `scripts/ngrok/ngrok.ringoo.v2.yml` — ngrok **v2** (`start-ringoo.ps1 -UseV2`)

Если зарезервированный домен другой — отредактируйте `url:` / `hostname:` в этих файлах.

## Ручной запуск (без скрипта)

```powershell
taskkill /IM ngrok.exe /F

ngrok start --config $env:LOCALAPPDATA\ngrok\ngrok.yml --config scripts/ngrok/ngrok.ringoo.yml --all
```

Панель: http://127.0.0.1:4040

## Makefile

```bash
make ngrok          # start-ringoo.ps1 (PowerShell)
make ngrok-sync     # только sync-ngrok-env.ps1
```

## Типичные ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| ERR_NGROK_334 | Тот же URL уже на другом туннеле | `taskkill /IM ngrok.exe /F`, запуск через `start-ringoo.ps1` |
| ERR_NGROK_9040 | IP не в whitelist ngrok | Dashboard → IP restrictions, или cloudflared |
| CORS / 400 Host | Django не знает ngrok-хост | `sync-ngrok-env.ps1` или добавьте `*.ngrok-free.dev` в `ALLOWED_HOSTS` |
| API с телефона не ходит | В `.env.local` остался `localhost:8000` | `sync-ngrok-env.ps1`, перезапуск frontend |

## Free plan: interstitial

Браузер может показывать страницу ngrok перед сайтом. API-клиент Ringoo отправляет заголовок `ngrok-skip-browser-warning` при запросах на `*.ngrok-free.dev`.

## Альтернатива

[Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/) — без лимита одного агента на бесплатном ngrok; см. обсуждение в команде при блокировке IP.
