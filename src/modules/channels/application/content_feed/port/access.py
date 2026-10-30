from typing import Protocol
from uuid import UUID


class FeedAccessPort(Protocol):
    """Ограничивает доступ одним фидом и использует существующий проектный Cipher."""

    def issue(self) -> tuple[bytes, bytes]:
        """Выдаёт hash и ciphertext случайного токена."""
        ...

    def matches(self, token: str, expected: bytes) -> bool:
        """Проверяет токен без раскрытия секрета."""
        ...

    def url(self, identifier: UUID, ciphertext: bytes) -> str:
        """Возвращает ссылку на каноническом публичном origin."""
        ...


class FeedAuthorizationPort(Protocol):
    """Проверяет текущие права владельца разрешения на канал и Files."""

    async def require(
        self, *, actor_id: UUID, channel_id: UUID, file_ids: tuple[UUID, ...]
    ) -> None:
        """Отказывает при отзыве роли или права на использованный файл."""
        ...
