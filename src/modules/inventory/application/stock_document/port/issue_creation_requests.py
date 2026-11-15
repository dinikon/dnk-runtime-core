from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID
from src.modules.inventory.application.stock_document.command.create_issue_draft.dto import (
    CreateIssueDraftResultDTO,
)


@dataclass(frozen=True, slots=True)
class IssueCreationClaim:
    """Возвращает захват ключа либо уже зафиксированный результат создания."""

    is_new: bool
    fingerprint: str
    result: CreateIssueDraftResultDTO | None


class IssueCreationRequestsPort(Protocol):
    """Сериализует повторные запросы на сессии внешнего UoW."""

    async def claim(
        self, actor_id: UUID, key: str, fingerprint: str, created_at: datetime
    ) -> IssueCreationClaim:
        """Захватывает ключ или читает результат после ожидания чужого commit."""
        ...

    async def complete(
        self, actor_id: UUID, key: str, result: CreateIssueDraftResultDTO
    ) -> None:
        """Сохраняет исходный результат до commit документа."""
        ...
