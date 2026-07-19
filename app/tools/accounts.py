"""Tool: list Yandex accounts for the current user."""

from mcp.server.fastmcp import Context

from app.context_parser import get_user_id_from_context
from app.services.account_service import account_service


async def list_yandex_accounts(ctx: Context) -> list[dict]:
    """Получить список всех настроенных Yandex-аккаунтов текущего пользователя.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - Всегда вызывай ПЕРВЫМ, чтобы узнать доступные account_id и service_type
    - Пользователь спрашивает "какие у меня аккаунты" или "покажи мои сервисы"
    - Нужно определить, какие сервисы Яндекса настроены у пользователя

    ПАРАМЕТРЫ:
    - Нет параметров. Метод автоматически определяет пользователя по контексту сессии.

    ВОЗВРАЩАЕТ:
    Массив объектов с полями:
    - id (int): account_id для передачи в другие инструменты
    - account_name (str): Название аккаунта (например, "Мой Директ")
    - service_type (str): Тип сервиса ("direct", "metrika", "audience", "webmaster", "admetrica")
    - is_active (bool): Активен ли аккаунт

    ПРИМЕР ИСПОЛЬЗОВАНИЯ:
    1. Вызови `list_yandex_accounts` — получишь массив account_id с service_type
    2. Выбери нужный service_type (например, "direct") и соответствующий account_id
    3. Передай account_id в соответствующий инструмент (get_direct_campaigns и т.д.)
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
