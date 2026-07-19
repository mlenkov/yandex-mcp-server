# Yandex MCP Server — Connection Info

> MCP-сервер для API Яндекса: Direct, Metrika, Audience, AdMetrica, Webmaster.
> Данные получены: 2026-07-19 (реальные JSON-RPC запросы к локальному серверу).

## Подключение

- **Endpoint:** `http://localhost:8000/mcp` (локально) / `https://app.mais.agency/mcp` (продакшн)
- **Transport:** Streamable HTTP (требует session-id, двухшаговая инициализация)
- **Auth:** `X-Bifrost-User-Id` header (через Bifrost Gateway)

### Инициализация сессии (Streamable HTTP)

```bash
# Шаг 1: получить session-id (первый запрос вернёт 400 + header)
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | head -1
# → mcp-session-id: <UUID>

# Шаг 2: использовать session-id во всех следующих запросах
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: <UUID>" \
  -d '{"jsonrpc":"2.0","id":2,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"cli","version":"1"}}}'

# Шаг 3: tools/list
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: <UUID>" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/list"}'
```

## Содержимое (фактические JSON-RPC дампы)

| Файл | Описание |
|---|---|
| `yandex-tools-dump.json` | Все 12 инструментов с полными inputSchema и description |
| `yandex-resources-dump.json` | Все 5 MCP Resources |
| `yandex-prompts-dump.json` | Все 3 MCP Prompts с аргументами |
| `yandex-resource-direct-docs.txt` | Содержимое `ReadResource(yandex://direct/docs)` — 1003 символа |
| `yandex-prompt-analyze.json` | Результат `GetPrompt(analyze_campaign_performance, campaign_id=12345, days=7)` |

## ListTools — 12 инструментов

| Инструмент | Описание |
|---|---|
| `ping` | Health check |
| `list_yandex_accounts` | Список аккаунтов пользователя |
| `get_direct_campaigns` | Кампании Яндекс Директа |
| `get_direct_stats` | Статистика кампании (Impressions, Clicks, CTR, CPC, Cost, Conversions) |
| `get_direct_keywords` | Ключевые слова кампании |
| `get_direct_ads` | Объявления кампании (Title, Text, Status, State) |
| `get_metrika_counters` | Счётчики Яндекс Метрики |
| `get_webmaster_hosts` | Хосты Яндекс Вебмастера |
| `get_audience_segments` | Сегменты Яндекс Аудитории |
| `get_admetrica_campaigns` | Кампании Яндекс AdMetrica |
| `update_account_context` | Обновить контекст аккаунта (бизнес-правила, заметки) |
| `get_account_context` | Получить контекст аккаунта |

Все инструменты имеют **rich LLM docstrings** в формате:

```
КОГДА ИСПОЛЬЗОВАТЬ:
- Сценарий использования

ПАРАМЕТРЫ:
- Описание каждого параметра

ВОЗВРАЩАЕТ:
- Что вернёт инструмент
```

## ListResources — 5 ресурсов

| Resource | Описание |
|---|---|
| `yandex://direct/docs` | Яндекс.Директ API: структура, статусы, ограничения |
| `yandex://metrika/docs` | Яндекс.Метрика API |
| `yandex://webmaster/docs` | Яндекс.Вебмастер API |
| `yandex://audience/docs` | Яндекс.Аудитории API |
| `yandex://admetrica/docs` | Яндекс.AdMetrica API |

## ListPrompts — 3 промпта

| Prompt | Аргументы | Описание |
|---|---|---|
| `analyze_campaign_performance` | `campaign_id` (int, required), `days` (int, default 7) | Детальный анализ кампании |
| `suggest_budget_optimization` | `account_id` (int, optional) | Перераспределение бюджета на основе ROI |
| `find_underperforming_ads` | `account_id` (int, optional) | Выявление неэффективных объявлений |

## Архитектура

```
FastMCP (Streamable HTTP) → async tools → AsyncYandexClient (apiforge) → Yandex API
                                    ├── Rate Limiter (30 req/min per user/tool)
                                    ├── Proactive Token Refresh (5 min before expiry)
                                    ├── Structured JSON Error Handling
                                    └── SQLAlchemy (account context, users, tokens)
```

## Обработка ошибок

Structured JSON с `yandex_api_error` флагом:

```json
{
  "status": "error",
  "yandex_api_error": true,
  "message": "Yandex API returned 401: Authentication failed",
  "suggestion": "Re-authorize the Yandex account via OAuth."
}
```

## Сравнение с Atlas MCP

Подробное сравнение — в [docs/atlas-mcp-connection.md](atlas-mcp-connection.md) и [README.md](../README.md#-why-this-is-better-than-atlas-mcp).
