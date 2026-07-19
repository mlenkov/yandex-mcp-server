# Atlas MCP — Connection Info

> Конкурентный MCP-сервер для Яндекс.Директа и других платформ.
> Данные получены: 2026-07-19 (токен: одноразовый, реальные JSON-RPC запросы).

## Подключение

- **Endpoint:** `https://atlas-mcp.ru/mcp`
- **Transport:** Streamable HTTP (без session-id, работает сразу)
- **Токен:** одноразовый, передаётся в заголовке `Authorization: Bearer <token>`

## Аутентификация

Все запросы требуют заголовок:

```
Authorization: Bearer <token>
```

## Документация

- `https://atlas-mcp.ru/docs/mcp/raw` — сырая документация (Markdown)
- Внутри MCP: `documentation_get` — читает docs по source/action

## Что внутри (фактические JSON-RPC дампы)

### ListTools — 23 инструмента

| Инструмент | Назначение |
|---|---|
| `documentation_get` | Читать документацию по source/action |
| `direct` | Generic read-only доступ к Яндекс.Директ (48 actions) |
| `metrica` | Generic read-only доступ к Яндекс.Метрике |
| `webmaster` | Generic read-only доступ к Яндекс.Вебмастеру |
| `appmetrica` | Generic read-only доступ к AppMetrica |
| `yandex_market` | Generic read-only доступ к Яндекс.Маркету |
| `wordstat` | Яндекс.Wordstat |
| `clickhouse` | ClickHouse queries |
| `bitrix` | Bitrix24 CRM |
| `topvisor` | Topvisor SEO |
| `amocrm` | amoCRM |
| `calltouch` | Calltouch |
| `roistat` | Roistat |
| `avito` / `avito_ads` | Avito |
| `ozon` / `ozon_performance` | Ozon |
| `vk_ads` | VK Ads |
| `wildberries` | Wildberries |
| `mindbox` | Mindbox |
| `unisender` | Unisender |
| `project_context` | Читать контекст проекта |
| `feedback` | Отправить feedback |

### ListResources → `[]` (нет ресурсов)
### ListPrompts → `[]` (нет промптов)

### Общая архитектура

Все source-инструменты имеют одинаковую сигнатуру:
```json
{
  "action": "string (required)",
  "account_id": "integer|string|null",
  "args": "object"
}
```

Документация по доступным actions — через `documentation_get`.

### Обработка ошибок

Структурированный JSON:
```json
{
  "code": "validation_error | unknown_action",
  "message": "Human-readable message with next steps",
  "retryable": false,
  "retry": {"strategy": "never", "immediate": false, "max_attempts": 0}
}
```

## Ключевые отличия от yandex-mcp-server

| Аспект | Atlas MCP | yandex-mcp-server |
|---|---|---|
| Архитектура | Один generic tool на платформу + action parameter | Отдельный tool на каждую операцию |
| Покрытие Яндекса | Direct, Metrika, Webmaster, AppMetrica, Market | **Direct, Metrika, Webmaster, Audience, AdMetrica** |
| Не-Яндекс | Bitrix24, amoCRM, Avito, Ozon, VK, Wildberries и др. | Нет |
| MCP Resources | **Нет** (через `documentation_get`) | **5 нативных** (`yandex://...`) |
| MCP Prompts | **Нет** | **3 нативных** (сценарии анализа) |
| Write-операции | **Read-only** | **Read + update** (account context) |
| Token Refresh | По факту 401 | **Proactive** (за 5 мин) |
| Rate Limiting | Не обнаружено | **30 req/min per user/tool** |
| Session ID | Не требуется | Требуется (Streamable HTTP) |

## Вывод

Atlas MCP выигрывает **широтой покрытия** (18+ платформ). yandex-mcp-server выигрывает **глубиной Yandex-экспертизы**: нативные MCP Resources/Prompts, конкретные инструменты с rich descriptions, proactive refresh, rate limiting, account context в БД.
