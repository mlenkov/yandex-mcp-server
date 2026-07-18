from cryptography.fernet import Fernet

from app.config import settings


class TokenCrypto:
    def __init__(self) -> None:
        self._fernet = Fernet(settings.fernet_key_resolved.encode())

    def encrypt(self, token: str) -> str:
        return self._fernet.encrypt(token.encode()).decode()

    def decrypt(self, encrypted_token: str) -> str:
        return self._fernet.decrypt(encrypted_token.encode()).decode()


crypto = TokenCrypto()
