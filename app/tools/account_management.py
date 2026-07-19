from mcp.server.fastmcp import Context

from app.context_parser import get_user_id_from_context
from app.services.account_service import account_service


async def update_account_context(account_id: int, context: str) -> dict:
    """Обновить контекст (мета-информацию) для аккаунта Яндекса.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Пользователь хочет добавить заметки к аккаунту
    - Нужно указать "это тестовый аккаунт" или "основной продакшн"
    - Нужно добавить бизнес-правила (например, "не трогать кампанию X")

    ПАРАМЕТРЫ:
    - account_id (int): ID аккаунта из list_yandex_accounts
    - context (str): Текстовое описание контекста (до 5000 символов)

    ПРИМЕР:
    update_account_context(42, "Основной аккаунт. Целевой CPA 500 руб.")

    ВОЗВРАЩАЕТ:
    {"status": "success", "message": "Context updated"}
    """
    try:
        await account_service.update_account_context(account_id, context)
        return {"status": "success", "message": "Context updated", "account_id": account_id}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Failed to update context: {e}"}


async def get_account_context(account_id: int) -> dict:
    """Получить контекст (мета-информацию) аккаунта Яндекса.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Перед выполнением действий с аккаунтом
    - Чтобы понять бизнес-правила и ограничения

    ВОЗВРАЩАЕТ:
    {"account_id": 42, "context": "Основной аккаунт..."}
    """
    try:
        context = await account_service.get_account_context(account_id)
        return {"account_id": account_id, "context": context or ""}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Failed to get context: {e}"}
