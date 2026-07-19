from __future__ import annotations

from datetime import datetime
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
    async def inject_token(**kwargs: Any) -> tuple[dict, dict]:
        params = kwargs.get("params") or {}
        headers = kwargs.get("headers") or {}
        headers["Authorization"] = f"OAuth {token}"
        return params, headers
    return inject_token


class AsyncYandexClient:
    def __init__(
        self,
        service_type: ServiceType,
        account_id: int,
        ctx: Any = None,
        timeout: float = 30.0,
    ) -> None:
        self.service_type = service_type
        self.account_id = account_id
        self.ctx = ctx
        self.timeout = timeout
        self._client: Optional[AsyncApiForgeClient] = None
        self._refreshed = False

    async def _ensure_client(self) -> AsyncApiForgeClient:
        if self._client is not None:
            return self._client

        token, expires_at = await account_service.get_account_token_with_expiry(
            self.account_id
        )

        if expires_at and (expires_at - datetime.utcnow()).total_seconds() < 300:
            if self.ctx:
                await self.ctx.warning(
                    f"Token for account {self.account_id} expires soon, refreshing proactively..."
                )
            token = await account_service.refresh_account_token(self.account_id)

        config_path = str(CONFIGS_DIR / f"{self.service_type.value}.json")
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
            if self.ctx:
                await self.ctx.info(
                    f"Calling {self.service_type.value}/{resource} for account {self.account_id}..."
                )
            response = await client.request(
                resource_name=resource,
                params=params,
                data=data,
                **kwargs,
            )
            return response.json()
        except ApiForgeAuthenticationError as e:
            if self._refreshed:
                msg = f"Yandex API returned {e.status_code}: token refresh failed"
                if self.ctx:
                    await self.ctx.error(msg)
                return {
                    "status": "error",
                    "yandex_api_error": True,
                    "message": msg,
                    "suggestion": "Re-authorize the Yandex account via OAuth.",
                }
            self._refreshed = True
            if self.ctx:
                await self.ctx.warning(
                    f"Token expired for account {self.account_id}, attempting refresh..."
                )
            try:
                new_token = await account_service.refresh_account_token(self.account_id)
                if self.ctx:
                    await self.ctx.info(
                        f"Token for account {self.account_id} refreshed successfully, retrying..."
                    )
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
            msg = f"Yandex API rate limit exceeded (retry after {e.retry_after}s)"
            if self.ctx:
                await self.ctx.warning(msg)
            return {
                "status": "error",
                "yandex_api_error": True,
                "message": msg,
                "suggestion": "Wait before making more requests.",
            }
        except ApiForgeRequestError as e:
            hint = "Check your request parameters against Yandex API documentation."
            if e.status_code == 400:
                hint = "Some parameters are invalid or missing."
            elif e.status_code == 429:
                hint = "Rate limit hit. Reduce request frequency."
            msg = f"Yandex API returned {e.status_code}: {e}"
            if self.ctx:
                await self.ctx.error(msg)
            return {
                "status": "error",
                "yandex_api_error": True,
                "message": msg,
                "suggestion": hint,
            }

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
