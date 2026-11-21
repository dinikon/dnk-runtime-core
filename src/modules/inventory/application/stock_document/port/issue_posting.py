from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID
from src.modules.inventory.application.stock_document.command.post_issue.dto import (
    PostIssueResultDTO,
)


@dataclass(frozen=True, slots=True)
class IssueCommandClaim:
    """Передаёт новый захват или исходный результат завершённого расхода."""

    is_new: bool
    fingerprint: str
    result: PostIssueResultDTO | None


class IssuePostingRequestsPort(Protocol):
    """Хранит ключ расхода, результат и связи SOURCE в общей транзакции."""

    async def claim(
        self, key: str, fingerprint: str, actor_id: UUID, created_at: datetime
    ) -> IssueCommandClaim:
        """Сериализует повтор до проверки нынешнего остатка."""
        ...

    async def complete(self, key: str, result: PostIssueResultDTO) -> None:
        """Фиксирует первоначальный ответ до внешнего commit."""
        ...

    async def add_links(self, links: tuple[tuple[UUID, UUID], ...]) -> None:
        """Связывает фактические строки с отрицательными записями Ledger."""
        ...
