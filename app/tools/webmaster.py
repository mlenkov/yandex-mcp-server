"""Tool: Yandex Webmaster — list hosts."""

from typing import Optional

from mcp.server.fastmcp import Context

from app.context_parser import get_user_id_from_context
from app.models import ServiceType
from app.services.account_service import account_service
from app.apiforge_async import AsyncYandexClient


async def get_webmaster_hosts(
    ctx: Context,
    account_id: Optional[int] = None,
) -> dict:
    """List hosts in Yandex Webmaster.

    Args:
        account_id: Optional Yandex account ID.
            Falls back to the first active Webmaster account when omitted.
    """
    user_id = get_user_id_from_context(ctx)

    if account_id is None:
        account_id, _ = await account_service.get_first_account_token(
            user_id, ServiceType.webmaster
        )

    client = AsyncYandexClient(ServiceType.webmaster, account_id)
    try:
        result = await client.request("hosts")
        return result
    finally:
        await client.close()
