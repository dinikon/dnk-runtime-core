from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID
from src.modules.inventory.application.stock_document.command.post_return.dto import (
    PostReturnResultDTO,
)


@dataclass(frozen=True, slots=True)
class ReturnCommandClaim:
    """Передаёт новый захват или исходный результат завершённого возврата."""

    is_new: bool
    fingerprint: str
    result: PostReturnResultDTO | None


class ReturnPostingRequestsPort(Protocol):
    """Хранит ключ возврата, результат и связи SOURCE/DESTINATION в общей транзакции."""

    async def claim(
        self, key: str, fingerprint: str, actor_id: UUID, created_at: datetime
    ) -> ReturnCommandClaim:
        """Сериализует повтор до проверки нынешнего остатка."""
        ...

    async def complete(self, key: str, result: PostReturnResultDTO) -> None:
        """Фиксирует первоначальный ответ до внешнего commit."""
        ...

    async def add_links(self, links: tuple[tuple[UUID, UUID, str], ...]) -> None:
        """Связывает фактические строки с обеими сторонами Ledger."""
        ...
