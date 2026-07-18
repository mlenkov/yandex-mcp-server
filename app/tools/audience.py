"""Tool: Yandex Audience — list segments."""

from typing import Optional

from mcp.server.fastmcp import Context

from app.context_parser import get_user_id_from_context
from app.models import ServiceType
from app.services.account_service import account_service
from app.apiforge_async import AsyncYandexClient


async def get_audience_segments(
    ctx: Context,
    account_id: Optional[int] = None,
    limit: int = 100,
) -> dict:
    """List segments in Yandex Audience.

    Args:
        account_id: Optional Yandex account ID.
            Falls back to the first active Audience account when omitted.
        limit: Maximum number of segments to return.
    """
    user_id = get_user_id_from_context(ctx)

    if account_id is None:
        try:
            account_id, _ = await account_service.get_first_account_token(
                user_id, ServiceType.audience
            )
        except ValueError as e:
            return {"error": True, "message": str(e)}

    client = AsyncYandexClient(ServiceType.audience, account_id)
    try:
        result = await client.request("segments")
        if isinstance(result, dict) and "segments" in result:
            result["segments"] = result["segments"][:limit]
        return result
    except Exception as e:
        return {"error": True, "message": f"Yandex Audience API error: {e}"}
    finally:
        await client.close()
