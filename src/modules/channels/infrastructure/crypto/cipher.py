import json
from cryptography.fernet import Fernet, InvalidToken
from src.modules.channels.application.error import ChannelSecretsUnavailableError


class ChannelSecretCipher:
    """Шифрует объект credentials отдельным ключом Fernet модуля Channels."""

    def __init__(self, key: str) -> None:
        """Принимает настроенный ключ, разрешая чтение публичных данных без него."""
        self._key = key

    def _cipher(self) -> Fernet:
        """Создаёт Fernet либо возвращает безопасную ошибку доступности хранилища."""
        if not self._key:
            raise ChannelSecretsUnavailableError(
                "Channel credentials storage is not configured."
            )
        try:
            return Fernet(self._key.encode("ascii"))
        except (ValueError, UnicodeError):
            raise ChannelSecretsUnavailableError(
                "Channel credentials storage is not configured."
            ) from None

    def encrypt(self, secrets: dict[str, str]) -> str:
        """Шифрует JSON-объект секретов, не изменяя исходные строки."""
        return self._cipher().encrypt(json.dumps(secrets).encode()).decode()

    def decrypt(self, encrypted: str) -> dict[str, str]:
        """Расшифровывает credentials; повреждение или неверный ключ даёт безопасную ошибку."""
        try:
            return json.loads(self._cipher().decrypt(encrypted.encode()))
        except (InvalidToken, ValueError, UnicodeError):
            raise ChannelSecretsUnavailableError(
                "Channel credentials cannot be read."
            ) from None
