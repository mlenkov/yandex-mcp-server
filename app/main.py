from mcp.server.fastmcp import FastMCP

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
)


@mcp.tool()
async def ping() -> str:
    return "pong"


@mcp.tool()
async def list_yandex_accounts_tool(ctx: mcp.Context) -> list[dict]:
    return await list_yandex_accounts(ctx)


@mcp.tool()
async def get_direct_campaigns_tool(
    ctx: mcp.Context,
    account_id: int | None = None,
) -> dict:
    return await get_direct_campaigns(ctx, account_id)


@mcp.tool()
async def get_metrika_counters_tool(
    ctx: mcp.Context,
    account_id: int | None = None,
) -> dict:
    return await get_metrika_counters(ctx, account_id)


@mcp.tool()
async def get_webmaster_hosts_tool(
    ctx: mcp.Context,
    account_id: int | None = None,
) -> dict:
    return await get_webmaster_hosts(ctx, account_id)


@mcp.tool()
async def get_audience_segments_tool(
    ctx: mcp.Context,
    account_id: int | None = None,
) -> dict:
    return await get_audience_segments(ctx, account_id)


@mcp.tool()
async def get_admetrica_campaigns_tool(
    ctx: mcp.Context,
    account_id: int | None = None,
) -> dict:
    return await get_admetrica_campaigns(ctx, account_id)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
