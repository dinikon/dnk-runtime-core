from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID
from src.modules.inventory.application.stock_document.command.post_internal_move.dto import (
    PostInternalMoveResultDTO,
)


@dataclass(frozen=True, slots=True)
class InternalMoveCommandClaim:
    """Передаёт новый захват или исходный результат завершённого перемещения."""

    is_new: bool
    fingerprint: str
    result: PostInternalMoveResultDTO | None


class InternalMovePostingRequestsPort(Protocol):
    """Хранит ключ перемещения, результат и связи SOURCE/DESTINATION в общей транзакции."""

    async def claim(
        self, key: str, fingerprint: str, actor_id: UUID, created_at: datetime
    ) -> InternalMoveCommandClaim:
        """Сериализует повтор до проверки нынешнего остатка."""
        ...

    async def complete(self, key: str, result: PostInternalMoveResultDTO) -> None:
        """Фиксирует первоначальный ответ до внешнего commit."""
        ...

    async def add_links(self, links: tuple[tuple[UUID, UUID, str], ...]) -> None:
        """Связывает фактические строки с обеими сторонами Ledger."""
        ...
