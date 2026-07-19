from typing import Optional

from mcp.server.fastmcp import Context

from app.context_parser import get_user_id_from_context
from app.models import ServiceType
from app.rate_limiter import rate_limiter
from app.services.account_service import account_service
from app.apiforge_async import AsyncYandexClient


async def get_metrika_counters(
    ctx: Context,
    account_id: Optional[int] = None,
    limit: int = 100,
) -> dict:
    """Получить список счётчиков Яндекс.Метрики.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает "покажи мои счётчики" или "какие счётчики у меня есть"
    - Нужно получить ID счётчика для запроса статистики или настройки
    - Нужно проверить, какие счётчики активны у пользователя

    ПАРАМЕТРЫ:
    - account_id (int, optional): ID аккаунта из `list_yandex_accounts`.
      Если не указан, используется первый доступный Metrika-аккаунт пользователя.
    - limit (int): Максимальное количество счётчиков в ответе.
      По умолчанию 100. НЕ превышай 500, чтобы не перегружать контекст LLM.

    ВОЗВРАЩАЕТ:
    dict с ключом 'counters', содержащим массив счётчиков.
    Каждый счётчик имеет поля:
    - id (int): Уникальный идентификатор счётчика
    - name (str): Название счётчика
    - site (str): URL сайта, на котором установлен счётчик
    - status (str): Статус счётчика

    ПРИМЕР ИСПОЛЬЗОВАНИЯ:
    1. Вызови `list_yandex_accounts`, чтобы узнать доступные account_id
    2. Вызови `get_metrika_counters(account_id=42, limit=50)` для получения списка
    3. Используй id счётчика для запроса статистики через другие инструменты

    RATE LIMIT: 30 запросов в минуту на пользователя
    """
    user_id = get_user_id_from_context(ctx)

    is_allowed, retry_after = await rate_limiter.check(user_id, "get_metrika_counters")
    if not is_allowed:
        return {
            "status": "error",
            "error_type": "rate_limit_exceeded",
            "message": f"Too many requests to get_metrika_counters. Please wait {retry_after} seconds.",
            "retry_after_seconds": retry_after,
            "suggestion": "Wait before trying again, or reduce the frequency of requests.",
        }

    if account_id is None:
        try:
            account_id, _ = await account_service.get_first_account_token(
                user_id, ServiceType.metrika
            )
        except ValueError as e:
            await ctx.error(f"No Metrika account found: {e}")
            return {"error": True, "message": str(e)}

    await ctx.info(f"Fetching Metrika counters for account {account_id}...")
    client = AsyncYandexClient(ServiceType.metrika, account_id, ctx=ctx)
    try:
        result = await client.request("counters")
        if isinstance(result, dict) and "counters" in result:
            result["counters"] = result["counters"][:limit]
            await ctx.info(f"Returned {len(result['counters'])} counters for account {account_id}")
        return result
    except Exception as e:
        await ctx.error(f"Failed to fetch Metrika counters: {e}")
        return {"error": True, "message": f"Yandex Metrika API error: {e}"}
    finally:
        await client.close()
