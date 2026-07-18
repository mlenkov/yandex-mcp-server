"""Tool: Yandex Metrika — list counters."""

from typing import Optional

from mcp.server.fastmcp import Context

from app.context_parser import get_user_id_from_context
from app.models import ServiceType
from app.services.account_service import account_service
from app.apiforge_async import AsyncYandexClient


async def get_metrika_counters(
    ctx: Context,
    account_id: Optional[int] = None,
) -> dict:
    """List counters in Yandex Metrika.

    Args:
        account_id: Optional Yandex account ID.
            Falls back to the first active Metrika account when omitted.
    """
    user_id = get_user_id_from_context(ctx)

    if account_id is None:
        account_id, _ = await account_service.get_first_account_token(
            user_id, ServiceType.metrika
        )

    client = AsyncYandexClient(ServiceType.metrika, account_id)
    try:
        result = await client.request("counters")
        return result
    finally:
        await client.close()
