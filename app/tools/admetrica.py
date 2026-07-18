"""Tool: Yandex AdMetrica — list campaigns."""

from typing import Optional

from mcp.server.fastmcp import Context

from app.context_parser import get_user_id_from_context
from app.models import ServiceType
from app.services.account_service import account_service
from app.apiforge_async import AsyncYandexClient


async def get_admetrica_campaigns(
    ctx: Context,
    account_id: Optional[int] = None,
    limit: int = 100,
) -> dict:
    """List campaigns in Yandex AdMetrica.

    Args:
        account_id: Optional Yandex account ID.
            Falls back to the first active AdMetrica account when omitted.
        limit: Maximum number of campaigns to return.
    """
    user_id = get_user_id_from_context(ctx)

    if account_id is None:
        try:
            account_id, _ = await account_service.get_first_account_token(
                user_id, ServiceType.admetrica
            )
        except ValueError as e:
            return {"error": True, "message": str(e)}

    client = AsyncYandexClient(ServiceType.admetrica, account_id)
    try:
        result = await client.request("campaigns")
        if isinstance(result, dict) and "campaigns" in result:
            result["campaigns"] = result["campaigns"][:limit]
        return result
    except Exception as e:
        return {"error": True, "message": f"Yandex AdMetrica API error: {e}"}
    finally:
        await client.close()
