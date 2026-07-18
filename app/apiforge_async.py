"""Async wrapper around apiforge that integrates with Yandex OAuth tokens."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from apiforge import AsyncApiForgeClient
from apiforge.exceptions import (
    ApiForgeRequestError,
    ApiForgeAuthenticationError,
    ApiForgeRateLimitError,
)

from app.models import ServiceType
from app.services.account_service import account_service

CONFIGS_DIR = Path(__file__).parent / "yandex_configs"


def _make_token_hook(token: str) -> Any:
    """Return a closure that injects an OAuth token into every request."""
    async def inject_token(**kwargs: Any) -> tuple[dict, dict]:
        params = kwargs.get("params") or {}
        headers = kwargs.get("headers") or {}
        headers["Authorization"] = f"OAuth {token}"
        return params, headers
    return inject_token


class AsyncYandexClient:
    """Async HTTP client for a single Yandex service, backed by apiforge.

    Automatically refreshes the OAuth token on 401 and retries once.

    Usage:
        client = AsyncYandexClient(ServiceType.direct, account_id=42)
        data = await client.request("campaigns", {"SelectionCriteria": {}})
    """

    def __init__(
        self,
        service_type: ServiceType,
        account_id: int,
        timeout: float = 30.0,
    ) -> None:
        self.service_type = service_type
        self.account_id = account_id
        self.timeout = timeout
        self._client: Optional[AsyncApiForgeClient] = None
        self._refreshed = False

    async def _ensure_client(self) -> AsyncApiForgeClient:
        remaining = await account_service.get_token_expires_remaining(self.account_id)
        if remaining < 300:
            await account_service.refresh_account_token(self.account_id)

        if self._client is not None:
            return self._client

        config_path = str(CONFIGS_DIR / f"{self.service_type.value}.json")
        token = await account_service.get_account_token(self.account_id)
        self._client = AsyncApiForgeClient(
            config_path=config_path,
            timeout=self.timeout,
            on_before_request=_make_token_hook(token),
        )
        return self._client

    async def request(
        self,
        resource: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[Any] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        client = await self._ensure_client()
        try:
            response = await client.request(
                resource_name=resource,
                params=params,
                data=data,
                **kwargs,
            )
            return response.json()
        except ApiForgeAuthenticationError as e:
            if self._refreshed:
                return {
                    "status": "error",
                    "yandex_api_error": True,
                    "message": f"Yandex API returned {e.status_code}: token refresh failed",
                    "suggestion": "Re-authorize the Yandex account via OAuth.",
                }
            self._refreshed = True
            try:
                new_token = await account_service.refresh_account_token(self.account_id)
            except Exception as refresh_err:
                return {
                    "status": "error",
                    "yandex_api_error": True,
                    "message": f"Token refresh failed: {refresh_err}",
                    "suggestion": "Check YANDEX_CLIENT_ID and YANDEX_CLIENT_SECRET in .env",
                }
            self._client = None
            return await self.request(resource, params, data, **kwargs)
        except ApiForgeRateLimitError as e:
            return {
                "status": "error",
                "yandex_api_error": True,
                "message": f"Yandex API rate limit exceeded (retry after {e.retry_after}s)",
                "suggestion": "Wait before making more requests.",
            }
        except ApiForgeRequestError as e:
            hint = "Check your request parameters against Yandex API documentation."
            if e.status_code == 400:
                hint = "Some parameters are invalid or missing."
            elif e.status_code == 429:
                hint = "Rate limit hit. Reduce request frequency."
            return {
                "status": "error",
                "yandex_api_error": True,
                "message": f"Yandex API returned {e.status_code}: {e}",
                "suggestion": hint,
            }

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
