import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from admin.app import app


@pytest.mark.asyncio
async def test_manual_add_rejects_invalid_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("httpx.AsyncClient") as mock_http:
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_http.return_value.__aenter__.return_value.post.return_value = mock_response

            resp = await client.post(
                "/admin/integrations/direct/add",
                data={
                    "account_name": "Test",
                    "login": "testuser",
                    "oauth_token": "invalid_token",
                    "context": "",
                },
                headers={"X-Forwarded-Email": "test@test.com"},
                follow_redirects=False,
            )
            assert resp.status_code != 303
