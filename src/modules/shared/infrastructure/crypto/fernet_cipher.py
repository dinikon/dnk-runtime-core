"""Единая реализация Fernet для секретов бизнес-модулей."""

from cryptography.fernet import Fernet, InvalidToken

from src.modules.shared.application.crypto.error import (
    CipherNotConfigured,
    CiphertextUnreadable,
)


class FernetCipher:
    """Сохраняет формат существующих бинарных и строковых Fernet-токенов."""

    def __init__(self, key: str | None) -> None:
        """Принимает постоянный ключ; новый ключ автоматически не создаётся."""
        self._cipher = Fernet(key.encode("ascii")) if key else None

    def require_configured(self) -> None:
        """Проверяет операционную конфигурацию независимо от потребителя."""
        if self._cipher is None:
            raise CipherNotConfigured("encryption_not_configured")

    def encrypt(self, plaintext: bytes) -> bytes:
        """Шифрует байты стандартным форматом Fernet."""
        self.require_configured()
        assert self._cipher is not None
        return self._cipher.encrypt(plaintext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        """Расшифровывает токен без раскрытия входа в ошибке."""
        self.require_configured()
        assert self._cipher is not None
        try:
            return self._cipher.decrypt(ciphertext)
        except InvalidToken:
            raise CiphertextUnreadable("ciphertext_unreadable") from None

    def encrypt_text(self, plaintext: str) -> str:
        """Сохраняет прежний строковый формат секретов Control Plane."""
        return self.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt_text(self, ciphertext: str) -> str:
        """Возвращает UTF-8 строку из существующего токена Control Plane."""
        try:
            return self.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except UnicodeError:
            raise CiphertextUnreadable("ciphertext_unreadable") from None
