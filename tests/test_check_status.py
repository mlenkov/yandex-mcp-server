import pytest
from unittest.mock import patch, AsyncMock
from admin.app import _check_account_status
from app.models import MCPYandexAccount, ServiceType
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_expired_token():
    acc = MCPYandexAccount(
        id=1, user_id=1, account_name="test",
        service_type=ServiceType.direct,
        encrypted_access_token="enc",
        token_expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        is_active=True,
    )
    status = await _check_account_status(acc)
    assert status["color"] == "red"
    assert "истёк" in status["message"].lower()


@pytest.mark.asyncio
async def test_valid_direct_token():
    acc = MCPYandexAccount(
        id=1, user_id=1, account_name="test",
        service_type=ServiceType.direct,
        encrypted_access_token="enc",
        token_expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        is_active=True,
    )
    with patch("admin.app.crypto") as mock_crypto, \
         patch("httpx.AsyncClient") as mock_client:
        mock_crypto.decrypt.return_value = "fake_token"
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"Clients": []}}
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        status = await _check_account_status(acc)
        assert status["valid"] is True
        assert status["color"] == "green"


@pytest.mark.asyncio
async def test_naive_datetime_handling():
    from datetime import datetime as dt

    acc = MCPYandexAccount(
        id=1, user_id=1, account_name="test",
        service_type=ServiceType.direct,
        encrypted_access_token="enc",
        token_expires_at=dt(2030, 1, 1),
        is_active=True,
    )

    with patch("admin.app.crypto") as mock_crypto, \
         patch("httpx.AsyncClient") as mock_client:
        mock_crypto.decrypt.return_value = "fake_token"
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"Clients": []}}
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        status = await _check_account_status(acc)
        assert status["valid"] is True or status["color"] in ["green", "orange"]
