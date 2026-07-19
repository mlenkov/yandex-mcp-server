from pathlib import Path

from pydantic_settings import BaseSettings
from typing import Optional, Tuple
from functools import cached_property
from cryptography.fernet import Fernet

from app.models import ServiceType


def _default_fernet_path() -> Path:
    docker_path = Path("/app/data/.fernet.key")
    if docker_path.parent.exists():
        return docker_path
    return Path("data/.fernet.key")


def _resolve_fernet_key(env_key: Optional[str]) -> str:
    if env_key:
        return env_key
    key_file = _default_fernet_path()
    if key_file.exists():
        return key_file.read_text().strip()
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key().decode()
    key_file.write_text(key)
    return key


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/yandex-mcp.db"

    # Encryption
    fernet_key: Optional[str] = None

    # Yandex OAuth — отдельные приложения для каждого сервиса
    yandex_direct_client_id: str = ""
    yandex_direct_client_secret: str = ""
    yandex_metrika_client_id: str = ""
    yandex_metrika_client_secret: str = ""
    yandex_webmaster_client_id: str = ""
    yandex_webmaster_client_secret: str = ""
    yandex_audience_client_id: str = ""
    yandex_audience_client_secret: str = ""
    yandex_admetrica_client_id: str = ""
    yandex_admetrica_client_secret: str = ""

    # Общий redirect_uri для всех сервисов
    yandex_redirect_uri: str = "https://app.mais.agency/admin/oauth/callback"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @cached_property
    def fernet_key_resolved(self) -> str:
        return _resolve_fernet_key(self.fernet_key)

    @cached_property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @cached_property
    def is_mysql(self) -> bool:
        return self.database_url.startswith("mysql")

    @cached_property
    def db_connect_args(self) -> dict:
        if self.is_sqlite:
            return {"check_same_thread": False}
        return {}

    def get_oauth_credentials(self, service_type: ServiceType) -> Tuple[str, str]:
        credentials_map = {
            ServiceType.direct: (self.yandex_direct_client_id, self.yandex_direct_client_secret),
            ServiceType.metrika: (self.yandex_metrika_client_id, self.yandex_metrika_client_secret),
            ServiceType.webmaster: (self.yandex_webmaster_client_id, self.yandex_webmaster_client_secret),
            ServiceType.audience: (self.yandex_audience_client_id, self.yandex_audience_client_secret),
            ServiceType.admetrica: (self.yandex_admetrica_client_id, self.yandex_admetrica_client_secret),
        }
        return credentials_map.get(service_type, ("", ""))


settings = Settings()
