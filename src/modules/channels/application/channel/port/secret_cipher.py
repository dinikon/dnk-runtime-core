from typing import Protocol


class SecretCipherPort(Protocol):
    """Защищает credentials, скрывая алгоритм и источник ключа от сценариев."""

    def encrypt(self, secrets: dict[str, str]) -> str:
        """Запечатывает секреты либо сообщает о недоступности ключа."""
        ...

    def decrypt(self, encrypted: str) -> dict[str, str]:
        """Раскрывает credentials только для объединения и проверки изменений."""
        ...
