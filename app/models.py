import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ServiceType(str, enum.Enum):
    direct = "direct"
    metrika = "metrika"
    admetrica = "admetrica"
    audience = "audience"
    webmaster = "webmaster"


class MCPUser(Base):
    __tablename__ = "mcp_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    yandex_accounts = relationship(
        "MCPYandexAccount", back_populates="user", cascade="all, delete-orphan"
    )


class MCPYandexAccount(Base):
    __tablename__ = "mcp_yandex_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("mcp_users.id", ondelete="CASCADE"), nullable=False
    )
    account_name = Column(String(255), nullable=False)
    service_type = Column(Enum(ServiceType), nullable=False)
    encrypted_access_token = Column(Text, nullable=False)
    encrypted_refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    account_context = Column(Text, nullable=True)

    user = relationship("MCPUser", back_populates="yandex_accounts")
