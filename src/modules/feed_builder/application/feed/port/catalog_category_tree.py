from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SourceCategoryDTO:
    """Передаёт узел исходного дерева текущего tenant."""

    id: UUID
    parent_id: UUID | None
    name: str


class CatalogCategoryTreePort(Protocol):
    """Читает локализованный снимок дерева через Catalog."""

    async def read(self, locale: str) -> tuple[SourceCategoryDTO, ...]:
        """Возвращает дерево одним запросом."""
        ...
