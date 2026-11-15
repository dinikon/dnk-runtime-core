from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID
from src.modules.inventory.application.stock_document.command.post_status_change.dto import (
    PostStatusChangeResultDTO,
)


@dataclass(frozen=True, slots=True)
class StatusChangeCommandClaim:
    """Передаёт новый захват или исходный результат завершённого изменения состояния."""

    is_new: bool
    fingerprint: str
    result: PostStatusChangeResultDTO | None


class StatusChangePostingRequestsPort(Protocol):
    """Хранит ключ изменения состояния, результат и связи SOURCE/DESTINATION в общей транзакции."""

    async def claim(
        self, key: str, fingerprint: str, actor_id: UUID, created_at: datetime
    ) -> StatusChangeCommandClaim:
        """Сериализует повтор до проверки нынешнего остатка."""
        ...

    async def complete(self, key: str, result: PostStatusChangeResultDTO) -> None:
        """Фиксирует первоначальный ответ до внешнего commit."""
        ...

    async def add_links(self, links: tuple[tuple[UUID, UUID, str], ...]) -> None:
        """Связывает фактические строки с обеими сторонами Ledger."""
        ...
