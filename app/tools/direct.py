from typing import Optional

from mcp.server.fastmcp import Context

from app.context_parser import get_user_id_from_context
from app.models import ServiceType
from app.rate_limiter import rate_limiter
from app.services.account_service import account_service
from app.apiforge_async import AsyncYandexClient


async def get_direct_campaigns(
    ctx: Context,
    account_id: Optional[int] = None,
    limit: int = 100,
) -> dict:
    """Получить список рекламных кампаний в Яндекс.Директе.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь спрашивает "как идут мои кампании?" или "покажи мои кампании"
    - Нужно узнать статус кампаний (активна/остановлена/черновик)
    - Нужно найти ID кампании для дальнейших действий (остановка, изменение бюджета)
    - Нужно получить общий список кампаний перед фильтрацией

    ПАРАМЕТРЫ:
    - account_id (int, optional): ID аккаунта из `list_yandex_accounts`.
      Если не указан, используется первый доступный Direct-аккаунт пользователя.
    - limit (int): Максимальное количество кампаний в ответе.
      По умолчанию 100. НЕ превышай 500, чтобы не перегружать контекст LLM.

    ВОЗВРАЩАЕТ:
    dict с ключом 'result', содержащим массив кампаний.
    Каждая кампания имеет поля:
    - Id (int): Уникальный идентификатор кампании
    - Name (str): Название кампании
    - Status (str): Статус (DRAFT, MODERATION, ACCEPTED, RUNNING, STOPPED)
    - StatusClarification (str): Уточнение статуса (если есть)

    ПРИМЕР ИСПОЛЬЗОВАНИЯ:
    1. Вызови `list_yandex_accounts`, чтобы узнать доступные account_id
    2. Вызови `get_direct_campaigns(account_id=42, limit=50)` для получения списка
    3. Если нужно остановить кампанию, используй её Id из ответа

    RATE LIMIT: 30 запросов в минуту на пользователя
    """
    user_id = get_user_id_from_context(ctx)

    is_allowed, retry_after = await rate_limiter.check(user_id, "get_direct_campaigns")
    if not is_allowed:
        return {
            "status": "error",
            "error_type": "rate_limit_exceeded",
            "message": f"Too many requests to get_direct_campaigns. Please wait {retry_after} seconds.",
            "retry_after_seconds": retry_after,
            "suggestion": "Wait before trying again, or reduce the frequency of requests.",
        }

    if account_id is None:
        try:
            account_id, _ = await account_service.get_first_account_token(
                user_id, ServiceType.direct
            )
        except ValueError as e:
            await ctx.error(f"No Direct account found: {e}")
            return {"error": True, "message": str(e)}

    await ctx.info(f"Fetching Direct campaigns for account {account_id}...")
    client = AsyncYandexClient(ServiceType.direct, account_id, ctx=ctx)
    try:
        result = await client.request(
            "campaigns",
            params={
                "FieldNames": ["Id", "Name", "Status", "StatusClarification"],
            },
        )
        if isinstance(result, dict) and "result" in result:
            items = result["result"].get("Campaigns", [])
            result["result"]["Campaigns"] = items[:limit]
            await ctx.info(f"Returned {len(items[:limit])} campaigns for account {account_id}")
        return result
    except Exception as e:
        await ctx.error(f"Failed to fetch Direct campaigns: {e}")
        return {"error": True, "message": f"Yandex Direct API error: {e}"}
    finally:
        await client.close()


async def get_direct_stats(
    ctx: Context,
    campaign_id: int,
    date_from: str,
    date_to: str,
    account_id: Optional[int] = None,
) -> dict:
    """Получить статистику по кампании Яндекс.Директа за период.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Нужно проанализировать эффективность кампании
    - Получить показы, клики, CTR, CPC, расходы, конверсии

    ПАРАМЕТРЫ:
    - campaign_id (int): ID кампании из get_direct_campaigns
    - date_from (str): Начало периода в формате YYYY-MM-DD
    - date_to (str): Конец периода в формате YYYY-MM-DD
    - account_id (int, optional): ID аккаунта. Автоопределение если не указан.

    ВОЗВРАЩАЕТ:
    dict с метриками: Impressions, Clicks, CTR, CPC, Cost, Conversions
    """
    user_id = get_user_id_from_context(ctx)
    is_allowed, retry_after = await rate_limiter.check(user_id, "get_direct_stats")
    if not is_allowed:
        return {"status": "error", "error_type": "rate_limit_exceeded",
                "message": f"Too many requests to get_direct_stats. Please wait {retry_after} seconds.",
                "retry_after_seconds": retry_after}

    if account_id is None:
        try:
            account_id, _ = await account_service.get_first_account_token(user_id, ServiceType.direct)
        except ValueError as e:
            return {"error": True, "message": str(e)}

    await ctx.info(f"Fetching stats for campaign {campaign_id} ({date_from} to {date_to})...")
    client = AsyncYandexClient(ServiceType.direct, account_id, ctx=ctx)
    try:
        result = await client.request("reports", params={
            "SelectionCriteria": {"Filter": [{"Field": "CampaignId", "Operator": "EQUALS", "Values": [str(campaign_id)]}]},
            "FieldNames": [
                "CampaignId", "CampaignName", "Date", "Impressions", "Clicks",
                "Ctr", "AverageCpc", "Cost", "Conversions", "ConversionRate",
                "CostPerConversion", "Profitability",
            ],
            "ReportName": f"campaign_stats_{campaign_id}_{date_from}_{date_to}",
            "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
            "DateRangeType": "CUSTOM_DATE",
            "Format": "TSV",
            "IncludeVAT": "NO",
            "IncludeDiscount": "NO",
        })
        await ctx.info(f"Stats received for campaign {campaign_id}")
        return result
    except Exception as e:
        await ctx.error(f"Failed to fetch stats for campaign {campaign_id}: {e}")
        return {"error": True, "message": f"Yandex Direct API error: {e}"}
    finally:
        await client.close()


async def get_direct_keywords(
    ctx: Context,
    campaign_id: int,
    account_id: Optional[int] = None,
    limit: int = 500,
) -> dict:
    """Получить список ключевых слов кампании Яндекс.Директа.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Нужно посмотреть ключевые слова кампании
    - Нужно найти ID ключевого слова для изменения ставки

    ПАРАМЕТРЫ:
    - campaign_id (int): ID кампании из get_direct_campaigns
    - account_id (int, optional): ID аккаунта
    - limit (int): Максимум фраз (1-1000, по умолч. 500)

    ВОЗВРАЩАЕТ: ключевые слова с Id, Keyword, Status, Bid, ContextualAdjustedBid
    """
    user_id = get_user_id_from_context(ctx)
    is_allowed, retry_after = await rate_limiter.check(user_id, "get_direct_keywords")
    if not is_allowed:
        return {"status": "error", "error_type": "rate_limit_exceeded",
                "message": f"Too many requests to get_direct_keywords. Please wait {retry_after} seconds.",
                "retry_after_seconds": retry_after}

    if account_id is None:
        try:
            account_id, _ = await account_service.get_first_account_token(user_id, ServiceType.direct)
        except ValueError as e:
            return {"error": True, "message": str(e)}

    await ctx.info(f"Fetching keywords for campaign {campaign_id}...")
    client = AsyncYandexClient(ServiceType.direct, account_id, ctx=ctx)
    try:
        result = await client.request("keywords", params={
            "SelectionCriteria": {"CampaignIds": [campaign_id]},
            "FieldNames": ["Id", "Keyword", "Status", "Bid", "ContextualAdjustedBid"],
            "Page": {"Limit": limit},
        })
        if isinstance(result, dict) and "result" in result:
            items = result["result"].get("Keywords", [])
            result["result"]["Keywords"] = items[:limit]
        return result
    except Exception as e:
        return {"error": True, "message": f"Yandex Direct API error: {e}"}
    finally:
        await client.close()


async def get_direct_ads(
    ctx: Context,
    campaign_id: int,
    account_id: Optional[int] = None,
    limit: int = 500,
) -> dict:
    """Получить список объявлений кампании Яндекс.Директа.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Нужно посмотреть все объявления кампании
    - Нужно найти ID объявления для модерации или изменения
    - Нужно проверить статус модерации объявлений

    ПАРАМЕТРЫ:
    - campaign_id (int): ID кампании из get_direct_campaigns
    - account_id (int, optional): ID аккаунта
    - limit (int): Максимум объявлений (1-1000, по умолч. 500)

    ВОЗВРАЩАЕТ: объявления с Id, Title, Text, Status, State, AdCategory
    """
    user_id = get_user_id_from_context(ctx)
    is_allowed, retry_after = await rate_limiter.check(user_id, "get_direct_ads")
    if not is_allowed:
        return {"status": "error", "error_type": "rate_limit_exceeded",
                "message": f"Too many requests to get_direct_ads. Please wait {retry_after} seconds.",
                "retry_after_seconds": retry_after}

    if account_id is None:
        try:
            account_id, _ = await account_service.get_first_account_token(user_id, ServiceType.direct)
        except ValueError as e:
            return {"error": True, "message": str(e)}

    await ctx.info(f"Fetching ads for campaign {campaign_id}...")
    client = AsyncYandexClient(ServiceType.direct, account_id, ctx=ctx)
    try:
        result = await client.request("ads", params={
            "SelectionCriteria": {"CampaignIds": [campaign_id]},
            "FieldNames": ["Id", "CampaignId", "AdGroupId", "Status", "State", "StatusClarification",
                           "Type", "Title", "Title2", "Text", "Href", "AdCategories"],
            "Page": {"Limit": limit},
        })
        if isinstance(result, dict) and "result" in result:
            items = result["result"].get("Ads", [])
            result["result"]["Ads"] = items[:limit]
        return result
    except Exception as e:
        return {"error": True, "message": f"Yandex Direct API error: {e}"}
    finally:
        await client.close()
