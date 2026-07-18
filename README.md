# Yandex MCP Server

MCP-сервер для API Яндекса: Direct, Metrika, Audience, AdMetrica, Webmaster.

**Архитектура:** FastMCP + apiforge async + SQLAlchemy (Dual DB: SQLite/MySQL)

## Быстрый старт (локально, SQLite)

```bash
# 1. Клонировать и перейти в директорию
cd yandex-mcp-server

# 2. Установить зависимости
uv sync --no-dev

# 3. Скопировать .env
cp .env.example .env

# 4. Сгенерировать Fernet-ключ (если не задан в .env)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Вставь ключ в .env: FERNET_KEY=...

# 5. Применить миграции
uv run alembic upgrade head

# 6. Запустить сервер
uv run python -m app.main
```

Сервер будет доступен на `http://localhost:8000/mcp` (Streamable HTTP).

## Production-деплой

```bash
# 0. Создать внешнюю Docker-сеть (только первый раз)
docker network create mais-bifrost-net

# 1. Скопировать production env
cp .env.prod.example .env.prod
# Заполнить: MYSQL_ROOT_PASSWORD, MYSQL_PASSWORD, FERNET_KEY, YANDEX_CLIENT_ID, YANDEX_CLIENT_SECRET

# 2. Запустить стек (сборка + запуск)
docker compose -f docker-compose.prod.yml up -d --build

# 3. Применить миграции
docker exec mais-yandex-mcp uv run alembic upgrade head

# 4. Проверить
curl http://localhost:8000/ping
```

## Настройка Bifrost

Bifrost должен проксировать заголовок `X-Bifrost-User-Id` при подключении к MCP-серверу. MCP-сервер слушает на `/mcp` (Streamable HTTP).

```caddy
app.mais.agency {
    # MCP endpoint
    reverse_proxy /mcp/* yandex-mcp:8000 {
        header_up X-Bifrost-User-Id {http.request.header.X-Bifrost-User-Id}
    }

    # Bifrost UI
    reverse_proxy /api/* mais-bifrost:8080
}
```

## Доступные MCP-инструменты

| Инструмент | Описание |
|-----------|----------|
| `ping` | Health check |
| `list_yandex_accounts` | Список аккаунтов пользователя |
| `get_direct_campaigns` | Кампании Яндекс Директа |
| `get_metrika_counters` | Счётчики Яндекс Метрики |
| `get_webmaster_hosts` | Хосты Яндекс Вебмастера |
| `get_audience_segments` | Сегменты Яндекс Аудитории |
| `get_admetrica_campaigns` | Кампании Яндекс AdMetrica |

## Отладка с MCP Inspector

Используй [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) для тестирования инструментов без LLM.

### Локальный запуск

```bash
# 1. Убедись, что в .env указан SQLite
# DATABASE_URL=sqlite+aiosqlite:///./data/yandex-mcp.db

# 2. Запусти сервер
uv run python -m app.main

# 3. В другом терминале запусти Inspector
npx @modelcontextprotocol/inspector

# 4. В браузере (http://localhost:5173) выбери:
#    Transport: Streamable HTTP
#    URL: http://localhost:8000/mcp

# 5. Перейди во вкладку Tools → List Tools → протестируй ping
```

### Тестирование ошибок

Если `apiforge` получает 400/401/429 от Яндекса, сервер возвращает структурированный JSON:

```json
{
  "status": "error",
  "yandex_api_error": true,
  "message": "Yandex API returned 401: Authentication failed",
  "suggestion": "Re-authorize the Yandex account via OAuth."
}
```

Ошибки выводятся в **ответе инструмента** (Response tab) и в **терминале сервера** (stdout).

### Полезные команды

```bash
# Проверить health
curl http://localhost:8000/ping

# Прямой запрос к MCP (JSON-RPC)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Структура проекта

```
app/
├── main.py                 # FastMCP + регистрация инструментов
├── config.py               # Pydantic Settings (Dual DB, Fernet, OAuth)
├── database.py             # SQLAlchemy async engine
├── models.py               # ORM: mcp_users, mcp_yandex_accounts
├── crypto.py               # TokenCrypto (Fernet)
├── context_parser.py       # X-Bifrost-User-Id из контекста
├── apiforge_async.py       # AsyncYandexClient + auto-refresh токенов
├── services/
│   └── account_service.py  # AccountService (DB + refresh OAuth)
├── tools/
│   ├── accounts.py         # list_yandex_accounts
│   ├── direct.py           # get_direct_campaigns
│   ├── metrika.py          # get_metrika_counters
│   ├── webmaster.py        # get_webmaster_hosts
│   ├── audience.py         # get_audience_segments
│   └── admetrica.py        # get_admetrica_campaigns
└── yandex_configs/         # JSON-конфиги для apiforge
```
