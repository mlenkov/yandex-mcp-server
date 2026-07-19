from typing import Optional

from mcp.server.fastmcp import Context

from app.context_parser import get_user_id_from_context
from app.models import ServiceType
from app.rate_limiter import rate_limiter
from app.services.account_service import account_service
from app.apiforge_async import AsyncYandexClient


async def get_admetrica_campaigns(
    ctx: Context,
    account_id: Optional[int] = None,
    limit: int = 100,
) -> dict:
    """Получить список рекламных кампаний в Яндекс.AdMetrica.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает "покажи мои кампании в AdMetrica"
    - Нужно узнать статус и показатели рекламных кампаний
    - Нужно найти ID кампании для дальнейшего анализа эффективности

    ПАРАМЕТРЫ:
    - account_id (int, optional): ID аккаунта из `list_yandex_accounts`.
      Если не указан, используется первый доступный AdMetrica-аккаунт пользователя.
    - limit (int): Максимальное количество кампаний в ответе.
      По умолчанию 100. НЕ превышай 500, чтобы не перегружать контекст LLM.

    ВОЗВРАЩАЕТ:
    dict с ключом 'campaigns', содержащим массив кампаний.
    Каждая кампания имеет поля:
    - id (int): Уникальный идентификатор кампании
    - name (str): Название кампании
    - status (str): Статус кампании
    - type (str): Тип кампании

    ПРИМЕР ИСПОЛЬЗОВАНИЯ:
    1. Вызови `list_yandex_accounts`, чтобы узнать доступные account_id
    2. Вызови `get_admetrica_campaigns(account_id=42, limit=50)` для получения списка
    3. Используй id кампании для запроса детальной статистики

    RATE LIMIT: 30 запросов в минуту на пользователя
    """
    user_id = get_user_id_from_context(ctx)

    is_allowed, retry_after = await rate_limiter.check(user_id, "get_admetrica_campaigns")
    if not is_allowed:
        return {
            "status": "error",
            "error_type": "rate_limit_exceeded",
            "message": f"Too many requests to get_admetrica_campaigns. Please wait {retry_after} seconds.",
            "retry_after_seconds": retry_after,
            "suggestion": "Wait before trying again, or reduce the frequency of requests.",
        }

    if account_id is None:
        try:
            account_id, _ = await account_service.get_first_account_token(
                user_id, ServiceType.admetrica
            )
        except ValueError as e:
            await ctx.error(f"No AdMetrica account found: {e}")
            return {"error": True, "message": str(e)}

    await ctx.info(f"Fetching AdMetrica campaigns for account {account_id}...")
    client = AsyncYandexClient(ServiceType.admetrica, account_id, ctx=ctx)
    try:
        result = await client.request("campaigns")
        if isinstance(result, dict) and "campaigns" in result:
            result["campaigns"] = result["campaigns"][:limit]
            await ctx.info(f"Returned {len(result['campaigns'])} campaigns for account {account_id}")
        return result
    except Exception as e:
        await ctx.error(f"Failed to fetch AdMetrica campaigns: {e}")
        return {"error": True, "message": f"Yandex AdMetrica API error: {e}"}
    finally:
        await client.close()
