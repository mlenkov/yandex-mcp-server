from mcp.server.fastmcp import FastMCP, Context

from app.config import settings
from app import models  # noqa: F401 – ensure models are loaded for Alembic
from app.tools.accounts import list_yandex_accounts
from app.tools.direct import get_direct_campaigns, get_direct_stats, get_direct_keywords, get_direct_ads
from app.tools.metrika import get_metrika_counters
from app.tools.webmaster import get_webmaster_hosts
from app.tools.audience import get_audience_segments
from app.tools.admetrica import get_admetrica_campaigns
from app.tools.account_management import update_account_context, get_account_context
from app.tools.wordstat import get_wordstat_stats
from app.tools.feedback import submit_feedback
from app.resources.yandex_docs import register_resources
from app.prompts.yandex_scenarios import register_prompts

mcp = FastMCP(
    "Yandex MCP Server",
    instructions="MCP server for Yandex API services: Direct, Metrika, Audience, AdMetrica, Webmaster",
    host="0.0.0.0",
)

register_resources(mcp)
register_prompts(mcp)


@mcp.tool(
    annotations={
        "title": "Ping",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def ping() -> str:
    """Проверить, что MCP-сервер работает и отвечает.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Для проверки здоровья сервера (healthcheck)
    - Перед началом работы, чтобы убедиться в доступности

    ВОЗВРАЩАЕТ: "pong"
    """
    return "pong"


@mcp.tool(
    annotations={
        "title": "List Yandex Accounts",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def list_yandex_accounts_tool(ctx: Context) -> list[dict]:
    """Получить список всех настроенных Yandex-аккаунтов текущего пользователя.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Всегда вызывай ПЕРВЫМ, чтобы узнать доступные account_id и service_type
    - Пользователь спрашивает "какие у меня аккаунты" или "покажи мои сервисы"

    ВОЗВРАЩАЕТ: Массив объектов с полями id, account_name, service_type, is_active.

    ПРИМЕР ИСПОЛЬЗОВАНИЯ:
    Вызови этот инструмент → получи account_id → передай в API-инструменты.
    """
    return await list_yandex_accounts(ctx)


@mcp.tool(
    annotations={
        "title": "Get Direct Campaigns",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_direct_campaigns_tool(
    ctx: Context,
    account_id: int | None = None,
    limit: int = 100,
) -> dict:
    """Получить список рекламных кампаний в Яндекс.Директе.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает о статусе кампаний, бюджетах
    - Нужно найти ID кампании для дальнейших действий

    ПАРАМЕТРЫ:
    - account_id: ID из list_yandex_accounts (опционально)
    - limit: Максимум кампаний (1-500, по умолч. 100)

    ВОЗВРАЩАЕТ: кампании с Id, Name, Status, StatusClarification.
    """
    return await get_direct_campaigns(ctx, account_id, limit)


@mcp.tool(
    annotations={
        "title": "Get Metrika Counters",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_metrika_counters_tool(
    ctx: Context,
    account_id: int | None = None,
    limit: int = 100,
) -> dict:
    """Получить список счётчиков Яндекс.Метрики.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает о счётчиках и статистике
    - Нужно получить ID счётчика для анализа данных

    ПАРАМЕТРЫ:
    - account_id: ID из list_yandex_accounts (опционально)
    - limit: Максимум счётчиков (1-500, по умолч. 100)

    ВОЗВРАЩАЕТ: счётчики с id, name, site, status.
    """
    return await get_metrika_counters(ctx, account_id, limit)


@mcp.tool(
    annotations={
        "title": "Get Webmaster Hosts",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_webmaster_hosts_tool(
    ctx: Context,
    account_id: int | None = None,
    limit: int = 100,
) -> dict:
    """Получить список сайтов (хостов) в Яндекс.Вебмастере.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает о сайтах и индексации
    - Нужно проверить статус верификации или индексации

    ПАРАМЕТРЫ:
    - account_id: ID из list_yandex_accounts (опционально)
    - limit: Максимум хостов (1-500, по умолч. 100)

    ВОЗВРАЩАЕТ: хосты с host_uid, host, verified, indexed.
    """
    return await get_webmaster_hosts(ctx, account_id, limit)


@mcp.tool(
    annotations={
        "title": "Get Audience Segments",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_audience_segments_tool(
    ctx: Context,
    account_id: int | None = None,
    limit: int = 100,
) -> dict:
    """Получить список сегментов аудитории в Яндекс.Аудиториях.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает о сегментах и аудиториях
    - Нужно найти ID сегмента для таргетинга

    ПАРАМЕТРЫ:
    - account_id: ID из list_yandex_accounts (опционально)
    - limit: Максимум сегментов (1-500, по умолч. 100)

    ВОЗВРАЩАЕТ: сегменты с id, name, type, size.
    """
    return await get_audience_segments(ctx, account_id, limit)


@mcp.tool(
    annotations={
        "title": "Get AdMetrica Campaigns",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_admetrica_campaigns_tool(
    ctx: Context,
    account_id: int | None = None,
    limit: int = 100,
) -> dict:
    """Получить список рекламных кампаний в Яндекс.AdMetrica.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает о кампаниях в AdMetrica
    - Нужно найти ID кампании для анализа

    ПАРАМЕТРЫ:
    - account_id: ID из list_yandex_accounts (опционально)
    - limit: Максимум кампаний (1-500, по умолч. 100)

    ВОЗВРАЩАЕТ: кампании с id, name, status, type.
    """
    return await get_admetrica_campaigns(ctx, account_id, limit)


@mcp.tool(
    annotations={
        "title": "Get Direct Stats",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_direct_stats_tool(
    ctx: Context,
    campaign_id: int,
    date_from: str,
    date_to: str,
    account_id: int | None = None,
) -> dict:
    """Получить статистику по кампании Яндекс.Директа за период.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Нужно проанализировать эффективность кампании
    - Получить показы, клики, CTR, CPC, расходы, конверсии

    ПАРАМЕТРЫ:
    - campaign_id: ID кампании из get_direct_campaigns
    - date_from: Начало периода в формате YYYY-MM-DD
    - date_to: Конец периода в формате YYYY-MM-DD
    - account_id: ID аккаунта (опционально)

    ВОЗВРАЩАЕТ: метрики Impressions, Clicks, CTR, CPC, Cost, Conversions.
    """
    return await get_direct_stats(ctx, campaign_id, date_from, date_to, account_id)


@mcp.tool(
    annotations={
        "title": "Get Direct Keywords",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_direct_keywords_tool(
    ctx: Context,
    campaign_id: int,
    account_id: int | None = None,
    limit: int = 500,
) -> dict:
    """Получить список ключевых слов кампании Яндекс.Директа.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Нужно посмотреть ключевые слова и ставки
    - Нужно найти ID фразы для изменения ставки

    ПАРАМЕТРЫ:
    - campaign_id: ID кампании из get_direct_campaigns
    - account_id: ID аккаунта (опционально)
    - limit: Максимум фраз (1-1000, по умолч. 500)

    ВОЗВРАЩАЕТ: ключевые слова с Id, Keyword, Status, Bid.
    """
    return await get_direct_keywords(ctx, campaign_id, account_id, limit)


@mcp.tool(
    annotations={
        "title": "Get Direct Ads",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_direct_ads_tool(
    ctx: Context,
    campaign_id: int,
    account_id: int | None = None,
    limit: int = 500,
) -> dict:
    """Получить список объявлений кампании Яндекс.Директа.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Нужно просмотреть все объявления кампании
    - Нужно проверить статус модерации

    ПАРАМЕТРЫ:
    - campaign_id: ID кампании из get_direct_campaigns
    - account_id: ID аккаунта (опционально)
    - limit: Максимум объявлений (1-1000, по умолч. 500)

    ВОЗВРАЩАЕТ: объявления с Id, Title, Text, Status, State.
    """
    return await get_direct_ads(ctx, campaign_id, account_id, limit)


@mcp.tool(
    annotations={
        "title": "Update Account Context",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def update_account_context_tool(account_id: int, context: str) -> dict:
    """Обновить контекст (мета-информацию) для аккаунта Яндекса.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь хочет добавить заметки к аккаунту
    - Нужно указать "это тестовый аккаунт" или "основной продакшн"
    - Нужно добавить бизнес-правила

    ПАРАМЕТРЫ:
    - account_id: ID аккаунта из list_yandex_accounts
    - context: Текстовое описание (до 5000 символов)

    ПРИМЕР: update_account_context(42, "Основной аккаунт. CPA 500 руб.")
    """
    return await update_account_context(account_id, context)


@mcp.tool(
    annotations={
        "title": "Get Account Context",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_account_context_tool(account_id: int) -> dict:
    """Получить контекст (мета-информацию) аккаунта Яндекса.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Перед выполнением действий с аккаунтом
    - Чтобы понять бизнес-правила и ограничения

    ВОЗВРАЩАЕТ: {"account_id": 42, "context": "..."}
    """
    return await get_account_context(account_id)


@mcp.tool(
    annotations={
        "title": "Get Wordstat Stats",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_wordstat_stats_tool(
    ctx: Context,
    query: str,
    region: str | None = None,
    account_id: int | None = None,
) -> dict:
    """Получить частотность ключевых слов через Яндекс.Wordstat.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Нужно узнать частотность ключевых слов перед запуском кампании
    - Подбор семантики для SEO и контекстной рекламы

    ПАРАМЕТРЫ:
    - query: Поисковый запрос (обязательно)
    - region: ID региона (опционально)
    - account_id: ID аккаунта Директа (опционально)

    ПРИМЕР: get_wordstat_stats("купить цветы", region=213)
    """
    return await get_wordstat_stats(ctx, query, region, account_id)


@mcp.tool(
    annotations={
        "title": "Submit Feedback",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def submit_feedback_tool(
    ctx: Context,
    reason: str,
    attempted_tool: str = "",
    agent_summary: str = "",
    account_id: int | None = None,
) -> dict:
    """Отправить обратную связь о работе MCP-сервера.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - LLM получила некорректный ответ или ошибку
    - Инструмент не сработал как ожидалось
    - Нужно сообщить о проблеме разработчикам

    ПАРАМЕТРЫ:
    - reason: Причина (tool_error, wrong_data, missing_feature, other)
    - attempted_tool: Имя инструмента
    - agent_summary: Краткое описание (до 500 символов)
    - account_id: ID аккаунта (опционально)

    ВОЗВРАЩАЕТ: {"status": "ok", "feedback_id": "uuid"}
    """
    return await submit_feedback(ctx, reason, attempted_tool, agent_summary, account_id)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
