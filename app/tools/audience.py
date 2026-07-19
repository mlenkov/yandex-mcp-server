from typing import Optional

from mcp.server.fastmcp import Context

from app.context_parser import get_user_id_from_context
from app.models import ServiceType
from app.rate_limiter import rate_limiter
from app.services.account_service import account_service
from app.apiforge_async import AsyncYandexClient


async def get_audience_segments(
    ctx: Context,
    account_id: Optional[int] = None,
    limit: int = 100,
) -> dict:
    """
    Получить список сегментов аудитории в Яндекс.Аудиториях.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает "какие у меня сегменты аудитории" или "покажи аудитории"
    - Нужно найти ID сегмента для использования в таргетинге кампаний
    - Нужно проверить, какие сегменты доступны для ретаргетинга

    ПАРАМЕТРЫ:
    - account_id (int, optional): ID аккаунта из `list_yandex_accounts`.
      Если не указан, используется первый доступный Audience-аккаунт пользователя.
    - limit (int): Максимальное количество сегментов в ответе.
      По умолчанию 100. НЕ превышай 500, чтобы не перегружать контекст LLM.

    ВОЗВРАЩАЕТ:
    dict с ключом 'segments', содержащим массив сегментов.
    Каждый сегмент имеет поля:
    - id (int): Уникальный идентификатор сегмента
    - name (str): Название сегмента
    - type (str): Тип сегмента (например, retargeting, interests)
    - size (int): Размер аудитории в сегменте

    ПРИМЕР ИСПОЛЬЗОВАНИЯ:
    1. Вызови `list_yandex_accounts`, чтобы узнать доступные account_id
    2. Вызови `get_audience_segments(account_id=42, limit=50)` для получения списка
    3. Используй id сегмента для настройки таргетинга в кампаниях Директа

    RATE LIMIT: 30 запросов в минуту на пользователя
    """
    user_id = get_user_id_from_context(ctx)

    is_allowed, retry_after = await rate_limiter.check(user_id, "get_audience_segments")
    if not is_allowed:
        return {
            "status": "error",
            "error_type": "rate_limit_exceeded",
            "message": f"Too many requests to get_audience_segments. Please wait {retry_after} seconds.",
            "retry_after_seconds": retry_after,
            "suggestion": "Wait before trying again, or reduce the frequency of requests.",
        }

    if account_id is None:
        try:
            account_id, _ = await account_service.get_first_account_token(
                user_id, ServiceType.audience
            )
        except ValueError as e:
            await ctx.error(f"No Audience account found: {e}")
            return {"error": True, "message": str(e)}

    await ctx.info(f"Fetching Audience segments for account {account_id}...")
    client = AsyncYandexClient(ServiceType.audience, account_id, ctx=ctx)
    try:
        result = await client.request("segments")
        if isinstance(result, dict) and "segments" in result:
            result["segments"] = result["segments"][:limit]
            await ctx.info(f"Returned {len(result['segments'])} segments for account {account_id}")
        return result
    except Exception as e:
        await ctx.error(f"Failed to fetch Audience segments: {e}")
        return {"error": True, "message": f"Yandex Audience API error: {e}"}
    finally:
        await client.close()
