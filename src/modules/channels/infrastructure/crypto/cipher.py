import json
from cryptography.fernet import Fernet, InvalidToken
from src.modules.channels.domain.error import ChannelSecretsUnavailableError


class ChannelSecretCipher:
    def __init__(self, key: str):
        self._key = key

    def _cipher(self):
        if not self._key:
            raise ChannelSecretsUnavailableError(
                "Channel credentials storage is not configured."
            )
        return Fernet(self._key.encode("ascii"))

    def encrypt(self, secrets: dict[str, str]) -> str:
        return self._cipher().encrypt(json.dumps(secrets).encode()).decode()

    def decrypt(self, encrypted: str) -> dict[str, str]:
        try:
            return json.loads(self._cipher().decrypt(encrypted.encode()))
        except (InvalidToken, ValueError, UnicodeError):
            raise ChannelSecretsUnavailableError(
                "Channel credentials cannot be read."
            ) from None
