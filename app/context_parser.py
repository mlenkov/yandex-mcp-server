"""FastMCP context parser for extracting user identity from Bifrost headers."""

from mcp.server.fastmcp import Context

DEFAULT_TEST_USER_ID = "test-user-1"


def get_user_id_from_context(ctx: Context) -> str:
    """Extract X-Bifrost-User-Id from the FastMCP request context.

    Falls back to DEFAULT_TEST_USER_ID when the header is absent
    (e.g. during local development).
    """
    try:
        request = ctx.request_context.request
        user_id = request.headers.get("X-Bifrost-User-Id")
        if user_id:
            return user_id
    except (AttributeError, Exception):
        pass
    return DEFAULT_TEST_USER_ID
