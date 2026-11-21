from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID
from src.modules.inventory.application.stock_document.command.post_write_off.dto import (
    PostWriteOffResultDTO,
)


@dataclass(frozen=True, slots=True)
class WriteOffCommandClaim:
    """Передаёт новый захват или исходный результат завершённого списания."""

    is_new: bool
    fingerprint: str
    result: PostWriteOffResultDTO | None


class WriteOffPostingRequestsPort(Protocol):
    """Хранит ключ списания, результат и связи SOURCE в общей транзакции."""

    async def claim(
        self, key: str, fingerprint: str, actor_id: UUID, created_at: datetime
    ) -> WriteOffCommandClaim:
        """Сериализует повтор до проверки нынешнего остатка."""
        ...

    async def complete(self, key: str, result: PostWriteOffResultDTO) -> None:
        """Фиксирует первоначальный ответ до внешнего commit."""
        ...

    async def add_links(self, links: tuple[tuple[UUID, UUID], ...]) -> None:
        """Связывает фактические строки с отрицательными записями Ledger."""
        ...
