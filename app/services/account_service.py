"""Account service — async DB access for Yandex accounts and token management."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy import select

from app.config import settings
from app.database import async_session_factory
from app.models import MCPUser, MCPYandexAccount, ServiceType
from app.crypto import crypto


class AccountService:
    def __init__(self) -> None:
        self._refresh_locks: dict[int, asyncio.Lock] = {}

    def _get_lock(self, account_id: int) -> asyncio.Lock:
        if account_id not in self._refresh_locks:
            self._refresh_locks[account_id] = asyncio.Lock()
        return self._refresh_locks[account_id]
    async def get_or_create_user(self, external_id: str) -> MCPUser:
        async with async_session_factory() as session:
            result = await session.execute(
                select(MCPUser).where(MCPUser.external_id == external_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                user = MCPUser(external_id=external_id)
                session.add(user)
                await session.commit()
                await session.refresh(user)
            return user

    async def get_user_accounts(
        self,
        external_id: str,
        service_type: Optional[ServiceType] = None,
    ) -> list[MCPYandexAccount]:
        async with async_session_factory() as session:
            user = await self.get_or_create_user(external_id)
            query = select(MCPYandexAccount).where(
                MCPYandexAccount.user_id == user.id,
                MCPYandexAccount.is_active == True,  # noqa: E712
            )
            if service_type is not None:
                query = query.where(MCPYandexAccount.service_type == service_type)
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_account(self, account_id: int) -> MCPYandexAccount:
        async with async_session_factory() as session:
            result = await session.execute(
                select(MCPYandexAccount).where(MCPYandexAccount.id == account_id)
            )
            account = result.scalar_one_or_none()
            if account is None:
                raise ValueError(f"Account {account_id} not found")
            return account

    async def get_account_token(self, account_id: int) -> str:
        account = await self.get_account(account_id)
        return crypto.decrypt(account.encrypted_access_token)

    async def get_token_expires_remaining(self, account_id: int) -> float:
        account = await self.get_account(account_id)
        if account.token_expires_at is None:
            return 3600.0
        remaining = (account.token_expires_at - datetime.utcnow()).total_seconds()
        return max(remaining, 0.0)

    async def get_first_account_token(
        self,
        external_id: str,
        service_type: ServiceType,
    ) -> tuple[int, str]:
        accounts = await self.get_user_accounts(external_id, service_type)
        if not accounts:
            raise ValueError(
                f"No active {service_type.value} account found for user {external_id}"
            )
        account = accounts[0]
        token = await self.get_account_token(account.id)
        return account.id, token

    async def refresh_account_token(self, account_id: int) -> str:
        lock = self._get_lock(account_id)
        async with lock:
            account = await self.get_account(account_id)
            remaining = (account.token_expires_at - datetime.utcnow()).total_seconds() if account.token_expires_at else 0
            if remaining > 60:
                return crypto.decrypt(account.encrypted_access_token)

            refresh_token = crypto.decrypt(account.encrypted_refresh_token) if account.encrypted_refresh_token else None
            if not refresh_token:
                raise ValueError(f"Account {account_id} has no refresh token")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth.yandex.ru/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": settings.yandex_client_id,
                    "client_secret": settings.yandex_client_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        new_access = data["access_token"]
        new_refresh = data.get("refresh_token", refresh_token)
        expires_in = data.get("expires_in", 3600)
        new_expires = datetime.utcnow() + timedelta(seconds=expires_in)

        async with async_session_factory() as session:
            account = await session.get(MCPYandexAccount, account_id)
            account.encrypted_access_token = crypto.encrypt(new_access)
            account.encrypted_refresh_token = crypto.encrypt(new_refresh)
            account.token_expires_at = new_expires
            await session.commit()

        return new_access


account_service = AccountService()
