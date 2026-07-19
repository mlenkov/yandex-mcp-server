from typing import Optional

from mcp.server.fastmcp import Context

from app.context_parser import get_user_id_from_context
from app.models import ServiceType
from app.rate_limiter import rate_limiter
from app.services.account_service import account_service
from app.apiforge_async import AsyncYandexClient


async def get_webmaster_hosts(
    ctx: Context,
    account_id: Optional[int] = None,
    limit: int = 100,
) -> dict:
    """Получить список сайтов (хостов) в Яндекс.Вебмастере.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает "какие мои сайты в Вебмастере" или "покажи хосты"
    - Нужно проверить статус индексации сайта
    - Нужно найти информацию о сайте для SEO-анализа

    ПАРАМЕТРЫ:
    - account_id (int, optional): ID аккаунта из `list_yandex_accounts`.
      Если не указан, используется первый доступный Webmaster-аккаунт пользователя.
    - limit (int): Максимальное количество хостов в ответе.
      По умолчанию 100. НЕ превышай 500, чтобы не перегружать контекст LLM.

    ВОЗВРАЩАЕТ:
    dict с ключом 'hosts', содержащим массив хостов.
    Каждый хост имеет поля:
    - host_uid (int): Уникальный идентификатор хоста
    - host (str): URL сайта (например, https://example.com)
    - verified (bool): Прошёл ли сайт верификацию
    - indexed (str): Статус индексации

    ПРИМЕР ИСПОЛЬЗОВАНИЯ:
    1. Вызови `list_yandex_accounts`, чтобы узнать доступные account_id
    2. Вызови `get_webmaster_hosts(account_id=42, limit=50)` для получения списка
    3. Используй host_uid для запроса детальной информации о сайте

    RATE LIMIT: 30 запросов в минуту на пользователя
    """
    user_id = get_user_id_from_context(ctx)

    is_allowed, retry_after = await rate_limiter.check(user_id, "get_webmaster_hosts")
    if not is_allowed:
        return {
            "status": "error",
            "error_type": "rate_limit_exceeded",
            "message": f"Too many requests to get_webmaster_hosts. Please wait {retry_after} seconds.",
            "retry_after_seconds": retry_after,
            "suggestion": "Wait before trying again, or reduce the frequency of requests.",
        }

    if account_id is None:
        try:
            account_id, _ = await account_service.get_first_account_token(
                user_id, ServiceType.webmaster
            )
        except ValueError as e:
            await ctx.error(f"No Webmaster account found: {e}")
            return {"error": True, "message": str(e)}

    await ctx.info(f"Fetching Webmaster hosts for account {account_id}...")
    client = AsyncYandexClient(ServiceType.webmaster, account_id, ctx=ctx)
    try:
        result = await client.request("hosts")
        if isinstance(result, dict) and "hosts" in result:
            result["hosts"] = result["hosts"][:limit]
            await ctx.info(f"Returned {len(result['hosts'])} hosts for account {account_id}")
        return result
    except Exception as e:
        await ctx.error(f"Failed to fetch Webmaster hosts: {e}")
        return {"error": True, "message": f"Yandex Webmaster API error: {e}"}
    finally:
        await client.close()
