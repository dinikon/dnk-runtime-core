from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class InventoryItemReferenceDTO:
    """Публичная ссылка на позицию без передачи её доменного агрегата."""

    id: UUID
    sku: str
    created: bool = False


class InventoryItemReferencesPort(Protocol):
    """Читает публичные проекции ссылок внутри общего tenant UoW."""

    async def find(self, sku: str) -> InventoryItemReferenceDTO | None:
        """Ищет точный канонический код без частичного совпадения."""
        ...

    async def read(
        self, identifiers: tuple[UUID, ...]
    ) -> tuple[InventoryItemReferenceDTO, ...]:
        """Читает ссылки одним batch без восстановления агрегатов."""
        ...

    async def search_ids(self, search: str) -> tuple[UUID, ...]:
        """Возвращает все совпавшие ID для фильтрации до пагинации потребителя."""
        ...
