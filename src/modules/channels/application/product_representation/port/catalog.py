from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.channels.application.product_representation.contracts import (
    RepresentationCatalogFamily,
)


class RepresentationCatalogPort(Protocol):
    """Изолирует многоязычное чтение Catalog на снимке внешнего UoW."""

    async def family(
        self, *, root_id: UUID, locales: tuple[str, ...], as_of: datetime
    ) -> RepresentationCatalogFamily | None:
        """Возвращает эффективный контент всех позиций без межъязыкового fallback."""
        ...
