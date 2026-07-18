"""Tool: list Yandex accounts for the current user."""

from mcp.server.fastmcp import Context

from app.context_parser import get_user_id_from_context
from app.services.account_service import account_service


async def list_yandex_accounts(ctx: Context) -> list[dict]:
    """Return all configured Yandex accounts for the current user.

    LLM calls this to discover available ``account_id`` values,
    then passes the chosen ``account_id`` to other tools.
    """
    user_id = get_user_id_from_context(ctx)
    accounts = await account_service.get_user_accounts(user_id)
    return [
        {
            "id": acc.id,
            "account_name": acc.account_name,
            "service_type": acc.service_type.value,
            "is_active": acc.is_active,
        }
        for acc in accounts
    ]
