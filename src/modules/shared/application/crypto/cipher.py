"""Общий порт шифрования секретов проекта."""

from typing import Protocol


class Cipher(Protocol):
    """Шифрует байты и UTF-8 строки одним постоянным ключом."""

    def require_configured(self) -> None:
        """Проверяет наличие ключа без расшифровки данных."""
        ...

    def encrypt(self, plaintext: bytes) -> bytes:
        """Шифрует бинарные данные без изменения их представления."""
        ...

    def decrypt(self, ciphertext: bytes) -> bytes:
        """Восстанавливает байты либо возвращает безопасную ошибку."""
        ...

    def encrypt_text(self, plaintext: str) -> str:
        """Шифрует UTF-8 строку в ASCII-представление токена."""
        ...

    def decrypt_text(self, ciphertext: str) -> str:
        """Восстанавливает строку из ASCII-представления токена."""
        ...
