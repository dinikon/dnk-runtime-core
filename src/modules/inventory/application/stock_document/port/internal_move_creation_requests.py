from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID
from src.modules.inventory.application.stock_document.command.create_internal_move_draft.dto import (
    CreateInternalMoveDraftResultDTO,
)


@dataclass(frozen=True, slots=True)
class InternalMoveCreationClaim:
    """Возвращает захват ключа либо уже зафиксированный результат создания."""

    is_new: bool
    fingerprint: str
    result: CreateInternalMoveDraftResultDTO | None


class InternalMoveCreationRequestsPort(Protocol):
    """Сериализует повторные запросы на сессии внешнего UoW."""

    async def claim(
        self, actor_id: UUID, key: str, fingerprint: str, created_at: datetime
    ) -> InternalMoveCreationClaim:
        """Захватывает ключ или читает результат после ожидания чужого commit."""
        ...

    async def complete(
        self, actor_id: UUID, key: str, result: CreateInternalMoveDraftResultDTO
    ) -> None:
        """Сохраняет исходный результат до commit документа."""
        ...
