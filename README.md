# Yandex MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-green)](https://modelcontextprotocol.io)
[![Docker](https://img.shields.io/badge/Docker-multi--stage-2496ED?logo=docker)](https://docker.com)

MCP-сервер для API Яндекса: Direct, Metrika, Audience, AdMetrica, Webmaster.

**Архитектура:** FastMCP + apiforge async + SQLAlchemy (Dual DB: SQLite/MySQL)

## 🏆 Why this is better than Atlas MCP

> Сравнение основано на **фактических JSON-RPC запросах** к Atlas MCP (2026-07-19, одноразовый токен).
> Полный анализ Atlas: [docs/atlas-mcp-connection.md](docs/atlas-mcp-connection.md).

| Фича | Atlas MCP | Yandex MCP Server (Ours) |
|---|---|---|
| **Архитектура** | Generic source tool (1 на платформу) + action parameter | **Отдельный tool на каждую операцию** с точными required/optional полями |
| **MCP Resources** | ❌ Нет. Документация через `documentation_get` | ✅ **5 нативных** (`yandex://direct/docs`, `yandex://metrika/docs`...) |
| **MCP Prompts** | ❌ Нет | ✅ **3 нативных** с типизированными аргументами |
| **Контекст аккаунта** | `project_context` (read-only) | ✅ **Read + Write** (`get_account_context`/`update_account_context`) |
| **Token Refresh** | По факту 401 | ✅ **Proactive** — за 5 мин до истечения |
| **Rate Limiting** | Не обнаружено | ✅ **30 req/min per user/per tool** |
| **Обработка ошибок** | Structured JSON (`validation_error`) | ✅ Structured JSON (`yandex_api_error`, `suggestion`, `retry_hint`) |
| **LLM docstrings** | Generic: "Read Yandex Direct data" | ✅ **Rich**: КОГДА ИСПОЛЬЗОВАТЬ / ПАРАМЕТРЫ / ВОЗВРАЩАЕТ / ПРИМЕР |
| **Write-операции** | ❌ Read-only | ✅ Update account context |
| **Yandex-покрытие** | Direct, Metrika, Webmaster, AppMetrica, Yandex Market | ✅ **Direct + Metrika + Webmaster + Audience + AdMetrica** |
| **Не-Яндекс** | ✅ Bitrix24, amoCRM, Avito, Ozon, VK, Wildberries (18+) | ❌ Только Яндекс |
| **Transport** | Streamable HTTP | ✅ Streamable HTTP (Docker-ready, Caddy reverse proxy) |

**Bottom line:** Atlas MCP выигрывает широтой (18+ платформ). Мы выигрываем **глубиной Yandex-экспертизы**: нативные Resources/Prompts, точные инструменты, proactive refresh, rate limiting, двусторонний контекст аккаунта.

> Все артефакты подтверждены фактическими JSON-RPC дампами (см. [Benchmark](#benchmark)).

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

## Доступные MCP-инструменты (12)

| Инструмент | Описание |
|-----------|----------|
| `ping` | Health check |
| `list_yandex_accounts` | Список аккаунтов пользователя |
| `get_direct_campaigns` | Кампании Яндекс Директа |
| `get_metrika_counters` | Счётчики Яндекс Метрики |
| `get_webmaster_hosts` | Хосты Яндекс Вебмастера |
| `get_audience_segments` | Сегменты Яндекс Аудитории |
| `get_admetrica_campaigns` | Кампании Яндекс AdMetrica |
| `get_direct_stats` | Статистика кампании (Impressions, Clicks, CTR, CPC, Cost, Conversions) |
| `get_direct_keywords` | Ключевые слова кампании |
| `get_direct_ads` | Объявления кампании (Title, Text, Status, State) |
| `get_account_context` | Получить контекст аккаунта (бизнес-правила, заметки) |
| `update_account_context` | Обновить контекст аккаунта |

## MCP Resources (5)

LLM может запросить документацию по API прямо во время диалога — без галлюцинаций:

| Resource | Описание |
|----------|----------|
| `yandex://direct/docs` | Яндекс.Директ API: структура, статусы, ограничения, best practices |
| `yandex://metrika/docs` | Яндекс.Метрика API |
| `yandex://webmaster/docs` | Яндекс.Вебмастер API |
| `yandex://audience/docs` | Яндекс.Аудитории API |
| `yandex://admetrica/docs` | Яндекс.AdMetrica API |

**Пример:** `ReadResource(yandex://direct/docs)` → возвращает ~1000 символов документации.

## MCP Prompts (3)

Готовые сценарии для LLM с типизированными аргументами:

| Prompt | Аргументы | Описание |
|--------|-----------|----------|
| `analyze_campaign_performance` | `campaign_id` (int), `days` (int, default 7) | Детальный анализ кампании с шагами и форматом отчёта |
| `suggest_budget_optimization` | `account_id` (int, optional) | Перераспределение бюджета на основе ROI |
| `find_underperforming_ads` | `account_id` (int, optional) | Выявление объявлений с CTR < 1%, CPC > avg, 0 конверсий |

**Пример:** `GetPrompt(analyze_campaign_performance, campaign_id=12345, days=7)` → возвращает message с инструкцией для LLM: "Проанализируй эффективность кампании 12345 за последние 7 дней. ШАГИ: 1. Получи контекст аккаунта... 2. Получи статистику..."

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

## Benchmark

> Фактические JSON-RPC дампы, доказывающие превосходство над Atlas MCP.
>
> Подключение: `POST http://localhost:8000/mcp` (Streamable HTTP, `Accept: application/json, text/event-stream`)

### 1. ListTools → `get_direct_stats_tool` (inputSchema + description)

```json
{
  "name": "get_direct_stats_tool",
  "description": "Получить статистику по кампании Яндекс.Директа за период.\n\n    КОГДА ИСПОЛЬЗОВАТЬ:\n    - Нужно проанализировать эффективность кампании\n    - Получить показы, клики, CTR, CPC, расходы, конверсии\n\n    ПАРАМЕТРЫ:\n    - campaign_id: ID кампании из get_direct_campaigns\n    - date_from: Начало периода в формате YYYY-MM-DD\n    - date_to: Конец периода в формате YYYY-MM-DD\n    - account_id: ID аккаунта (опционально)\n\n    ВОЗВРАЩАЕТ: метрики Impressions, Clicks, CTR, CPC, Cost, Conversions.",
  "inputSchema": {
    "properties": {
      "campaign_id": {"type": "integer"},
      "date_from": {"type": "string"},
      "date_to": {"type": "string"},
      "account_id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": null}
    },
    "required": ["campaign_id", "date_from", "date_to"]
  }
}
```

### 2. ListResources

```json
{
  "resources": [
    {"name": "direct_docs",    "uri": "yandex://direct/docs",    "mimeType": "text/plain"},
    {"name": "metrika_docs",   "uri": "yandex://metrika/docs",   "mimeType": "text/plain"},
    {"name": "webmaster_docs", "uri": "yandex://webmaster/docs", "mimeType": "text/plain"},
    {"name": "audience_docs",  "uri": "yandex://audience/docs",  "mimeType": "text/plain"},
    {"name": "admetrica_docs", "uri": "yandex://admetrica/docs", "mimeType": "text/plain"}
  ]
}
```

### 3. ReadResource → `yandex://direct/docs`

```
# Яндекс.Директ API — Полная документация

## Структура данных
- Кампания (Campaign) → Группы (AdGroups) → Объявления (Ads) + Фразы (Keywords)
- Каждая кампания имеет: Id, Name, Status, StartDate, DailyBudget

## Статусы кампаний
- DRAFT — черновик, не запущена
- MODERATION — на проверке
- ACCEPTED — принята, готова к запуску
- RUNNING — активна, показываются объявления
- STOPPED — остановлена вручную
- ENDED — завершена (закончился бюджет или дата)

## Ограничения API
- Максимум 10000 объектов ...
```
*Полная длина: 1003 символа.*

### 4. ListPrompts

```json
{
  "prompts": [
    {
      "name": "analyze_campaign_performance",
      "description": "Анализ эффективности рекламной кампании за последние N дней.",
      "arguments": [
        {"name": "campaign_id", "required": true},
        {"name": "days", "required": false}
      ]
    },
    {
      "name": "suggest_budget_optimization",
      "description": "Предложения по оптимизации бюджета рекламных кампаний.",
      "arguments": [{"name": "account_id", "required": false}]
    },
    {
      "name": "find_underperforming_ads",
      "description": "Поиск неэффективных объявлений для оптимизации.",
      "arguments": [{"name": "account_id", "required": false}]
    }
  ]
}
```

### 5. GetPrompt → `analyze_campaign_performance(campaign_id=12345, days=7)`

```json
{
  "description": "Анализ эффективности рекламной кампании за последние N дней.",
  "messages": [{
    "role": "user",
    "content": {
      "type": "text",
      "text": "Проанализируй эффективность кампании 12345 за последние 7 дней.\n\nШАГИ:\n1. Получи контекст аккаунта через get_account_context\n2. Получи статистику кампании за период (используй get_direct_stats)\n3. Получи статистику за предыдущий аналогичный период для сравнения\n4. Рассчитай ключевые метрики: CTR, CPC, CR, CPA, ROI\n5. Выяви аномалии (резкие падения/росты)\n6. Предложи конкретные оптимизации\n\nФОРМАТ ОТВЕТА:\n- Краткое резюме (1-2 предложения)\n- Ключевые метрики (таблица)\n- Сравнение с предыдущим периодом\n- Выявленные проблемы\n- Рекомендации (приоритизированные)"
    }
  }]
}
```

### Полезные команды

```bash
# Проверить health
curl http://localhost:8000/ping

# Прямой запрос к MCP (JSON-RPC)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Contributing

1. Форкни репозиторий и создай ветку: `git checkout -b feature/my-feature`
2. Установи dev-зависимости: `uv sync`
3. Убедись, что тесты проходят: `uv run pytest`
4. Открой Pull Request

## License

MIT License — см. [LICENSE](LICENSE).

### Seed-данные для тестирования

Наполни SQLite тестовым пользователем с аккаунтом Директа (токен истёк вчера — триггернет auto-refresh):

```bash
uv run python -m scripts.seed
```

После этого в Inspector при вызове `get_direct_campaigns`:
1. Сервер получит 401 от Яндекса
2. Попробует обновить токен через `refresh_account_token`
3. Вернёт структурированную ошибку с `"yandex_api_error": true`

## Структура проекта

```
app/
├── main.py                 # FastMCP + регистрация инструментов/ресурсов/промптов
├── config.py               # Pydantic Settings (Dual DB, Fernet, OAuth)
├── database.py             # SQLAlchemy async engine
├── models.py               # ORM: mcp_users, mcp_yandex_accounts (+ account_context)
├── crypto.py               # TokenCrypto (Fernet)
├── context_parser.py       # X-Bifrost-User-Id из контекста
├── apiforge_async.py       # AsyncYandexClient + auto-refresh + ctx.logging
├── rate_limiter.py         # In-memory per-user/per-tool rate limiter (30 req/min)
├── services/
│   └── account_service.py  # AccountService (DB + refresh OAuth + context)
├── tools/
│   ├── accounts.py         # list_yandex_accounts
│   ├── direct.py           # get_direct_campaigns | stats | keywords | ads
│   ├── metrika.py          # get_metrika_counters
│   ├── webmaster.py        # get_webmaster_hosts
│   ├── audience.py         # get_audience_segments
│   ├── admetrica.py        # get_admetrica_campaigns
│   └── account_management.py  # get/update_account_context
├── resources/
│   └── yandex_docs.py      # MCP Resources: 5 API documentation endpoints
├── prompts/
│   └── yandex_scenarios.py # MCP Prompts: 3 analysis scenarios
└── yandex_configs/         # JSON-конфиги для apiforge
```
