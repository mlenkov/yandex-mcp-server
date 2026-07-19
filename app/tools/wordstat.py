from typing import Optional

from mcp.server.fastmcp import Context

from app.context_parser import get_user_id_from_context
from app.models import ServiceType
from app.rate_limiter import rate_limiter
from app.services.account_service import account_service
from app.apiforge_async import AsyncYandexClient


async def get_wordstat_stats(
    ctx: Context,
    query: str,
    region: Optional[str] = None,
    account_id: Optional[int] = None,
) -> dict:
    """Получить частотность ключевых слов через Яндекс.Wordstat."""
    user_id = get_user_id_from_context(ctx)
    is_allowed, retry_after = await rate_limiter.check(user_id, "get_wordstat_stats")
    if not is_allowed:
        return {
            "status": "error",
            "error_type": "rate_limit_exceeded",
            "retry_after_seconds": retry_after,
        }
    if account_id is None:
        try:
            account_id, _ = await account_service.get_first_account_token(
                user_id, ServiceType.direct
            )
        except ValueError as e:
            await ctx.error(f"No Direct account found: {e}")
            return {"error": True, "message": str(e)}
    kwargs: dict = {}
    if region:
        kwargs["region_id"] = region
    client = AsyncYandexClient(ServiceType.direct, account_id, ctx=ctx)
    report_data = await client.request("reports", {
        "params": {
            "SelectionCriteria": {},
            "FieldNames": ["Keyword", "Clicks", "Impressions"],
            "Page": {"Limit": 1},
            "ReportName": f"wordstat_{query[:20]}",
            "ReportType": "SEARCH_QUERY_PERFORMANCE_REPORT",
            "DateRangeType": "LAST_30_DAYS",
            "Format": "TSV",
        }
    })
    await client.close()
    return report_data
