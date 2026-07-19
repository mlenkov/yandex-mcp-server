from mcp.server.fastmcp import FastMCP, Context

from app.config import settings
from app import models  # noqa: F401 – ensure models are loaded for Alembic
from app.tools.accounts import list_yandex_accounts
from app.tools.direct import get_direct_campaigns
from app.tools.metrika import get_metrika_counters
from app.tools.webmaster import get_webmaster_hosts
from app.tools.audience import get_audience_segments
from app.tools.admetrica import get_admetrica_campaigns

mcp = FastMCP(
    "Yandex MCP Server",
    instructions="MCP server for Yandex API services: Direct, Metrika, Audience, AdMetrica, Webmaster",
    host="0.0.0.0",
)


@mcp.tool()
async def ping() -> str:
    """
    Проверить, что MCP-сервер работает и отвечает.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Для проверки здоровья сервера (healthcheck)
    - Перед началом работы, чтобы убедиться в доступности

    ВОЗВРАЩАЕТ: "pong"
    """
    return "pong"


@mcp.tool()
async def list_yandex_accounts_tool(ctx: Context) -> list[dict]:
    """
    Получить список всех настроенных Yandex-аккаунтов текущего пользователя.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Всегда вызывай ПЕРВЫМ, чтобы узнать доступные account_id и service_type
    - Пользователь спрашивает "какие у меня аккаунты" или "покажи мои сервисы"

    ВОЗВРАЩАЕТ: Массив объектов с полями id, account_name, service_type, is_active.

    ПРИМЕР ИСПОЛЬЗОВАНИЯ:
    Вызови этот инструмент → получи account_id → передай в API-инструменты.
    """
    return await list_yandex_accounts(ctx)


@mcp.tool()
async def get_direct_campaigns_tool(
    ctx: Context,
    account_id: int | None = None,
    limit: int = 100,
) -> dict:
    """
    Получить список рекламных кампаний в Яндекс.Директе.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает о статусе кампаний, бюджетах
    - Нужно найти ID кампании для дальнейших действий

    ПАРАМЕТРЫ:
    - account_id: ID из list_yandex_accounts (опционально)
    - limit: Максимум кампаний (1-500, по умолч. 100)

    ВОЗВРАЩАЕТ: кампании с Id, Name, Status, StatusClarification.
    """
    return await get_direct_campaigns(ctx, account_id, limit)


@mcp.tool()
async def get_metrika_counters_tool(
    ctx: Context,
    account_id: int | None = None,
    limit: int = 100,
) -> dict:
    """
    Получить список счётчиков Яндекс.Метрики.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает о счётчиках и статистике
    - Нужно получить ID счётчика для анализа данных

    ПАРАМЕТРЫ:
    - account_id: ID из list_yandex_accounts (опционально)
    - limit: Максимум счётчиков (1-500, по умолч. 100)

    ВОЗВРАЩАЕТ: счётчики с id, name, site, status.
    """
    return await get_metrika_counters(ctx, account_id, limit)


@mcp.tool()
async def get_webmaster_hosts_tool(
    ctx: Context,
    account_id: int | None = None,
    limit: int = 100,
) -> dict:
    """
    Получить список сайтов (хостов) в Яндекс.Вебмастере.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает о сайтах и индексации
    - Нужно проверить статус верификации или индексации

    ПАРАМЕТРЫ:
    - account_id: ID из list_yandex_accounts (опционально)
    - limit: Максимум хостов (1-500, по умолч. 100)

    ВОЗВРАЩАЕТ: хосты с host_uid, host, verified, indexed.
    """
    return await get_webmaster_hosts(ctx, account_id, limit)


@mcp.tool()
async def get_audience_segments_tool(
    ctx: Context,
    account_id: int | None = None,
    limit: int = 100,
) -> dict:
    """
    Получить список сегментов аудитории в Яндекс.Аудиториях.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает о сегментах и аудиториях
    - Нужно найти ID сегмента для таргетинга

    ПАРАМЕТРЫ:
    - account_id: ID из list_yandex_accounts (опционально)
    - limit: Максимум сегментов (1-500, по умолч. 100)

    ВОЗВРАЩАЕТ: сегменты с id, name, type, size.
    """
    return await get_audience_segments(ctx, account_id, limit)


@mcp.tool()
async def get_admetrica_campaigns_tool(
    ctx: Context,
    account_id: int | None = None,
    limit: int = 100,
) -> dict:
    """
    Получить список рекламных кампаний в Яндекс.AdMetrica.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает о кампаниях в AdMetrica
    - Нужно найти ID кампании для анализа

    ПАРАМЕТРЫ:
    - account_id: ID из list_yandex_accounts (опционально)
    - limit: Максимум кампаний (1-500, по умолч. 100)

    ВОЗВРАЩАЕТ: кампании с id, name, status, type.
    """
    return await get_admetrica_campaigns(ctx, account_id, limit)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
