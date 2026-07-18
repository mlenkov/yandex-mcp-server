"""Seed script: populate SQLite with test data for MCP Inspector."""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete

from app.database import async_session_factory
from app.models import MCPUser, MCPYandexAccount, ServiceType
from app.crypto import crypto

TEST_USER_ID = "test-user-1"


async def seed() -> None:
    async with async_session_factory() as session:
        existing = await session.execute(
            select(MCPUser).where(MCPUser.external_id == TEST_USER_ID)
        )
        user = existing.scalar_one_or_none()

        if user is not None:
            await session.execute(
                delete(MCPYandexAccount).where(MCPYandexAccount.user_id == user.id)
            )
            await session.delete(user)
            await session.commit()

        user = MCPUser(external_id=TEST_USER_ID)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        account = MCPYandexAccount(
            user_id=user.id,
            account_name="Test Direct",
            service_type=ServiceType.direct,
            encrypted_access_token=crypto.encrypt("fake_expired_token"),
            encrypted_refresh_token=crypto.encrypt("fake_refresh_token"),
            token_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            is_active=True,
        )
        session.add(account)
        await session.commit()

    print(f"✅ Seeded user '{TEST_USER_ID}' with 1 Direct account (token expired yesterday)")
    print(f"   → Next tool call will trigger 401 → auto-refresh → log the error in Inspector")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
