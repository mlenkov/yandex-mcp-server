import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import Context

FEEDBACK_PATH = Path("/app/data/feedback.jsonl")

logger = logging.getLogger("yandex-mcp.feedback")


async def submit_feedback(
    ctx: Context,
    reason: str,
    attempted_tool: str = "",
    agent_summary: str = "",
    account_id: int | None = None,
) -> dict:
    """Отправить обратную связь о работе MCP-сервера.

    КОГДА ИСПОЛЬЗОВАТЬ:
    - LLM получила некорректный ответ или ошибку
    - Инструмент не сработал как ожидалось
    - Нужно сообщить о проблеме разработчикам

    ПАРАМЕТРЫ:
    - reason: Причина фидбека (обязательно). Варианты: "tool_error", "wrong_data", "missing_feature", "other"
    - attempted_tool: Имя инструмента, с которым была проблема
    - agent_summary: Краткое описание от агента (30-200 символов)
    - account_id: ID аккаунта (если применимо)

    ВОЗВРАЩАЕТ: {"status": "ok", "feedback_id": "uuid"}
    """
    import uuid

    feedback_id = str(uuid.uuid4())
    entry = {
        "feedback_id": feedback_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "attempted_tool": attempted_tool,
        "agent_summary": agent_summary[:500],
        "account_id": account_id,
    }
    try:
        FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(FEEDBACK_PATH, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info("Feedback saved: %s", feedback_id)
    except OSError as e:
        logger.warning("Failed to save feedback: %s", e)
    return {"status": "ok", "feedback_id": feedback_id}
