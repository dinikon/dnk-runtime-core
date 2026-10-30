from typing import Protocol
from uuid import UUID


class MediaAuthorizationPort(Protocol):
    """Проверяет право инициатора использовать каждый выбранный файл."""

    async def require_files(self, file_ids: tuple[UUID, ...]) -> None:
        """Проверяет Files ACL до выдачи внешних URL."""
        ...


class MediaTokenPort(Protocol):
    """Выдаёт, проверяет и восстанавливает ограниченные секреты через Shared Cipher."""

    def issue(self) -> tuple[bytes, bytes]:
        """Возвращает hash и ciphertext без сохранения plaintext в Domain."""
        ...

    def matches(self, token: str, expected: bytes) -> bool:
        """Сравнивает случайный токен без утечки в ошибки."""
        ...

    def url(self, identifier: UUID, ciphertext: bytes, content_type: str) -> str:
        """Строит URL на доверенном tenant API host, не на произвольном Host запроса."""
        ...
