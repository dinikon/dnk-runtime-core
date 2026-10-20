from typing import Protocol
from uuid import UUID
from src.modules.channels.application.product_representation.contracts import (
    CatalogDraftValuesDTO,
    CatalogDraftCheckDTO,
)


class CatalogDraftCreationFacade(Protocol):
    """Предоставляет ядру Channels атомарное создание и проверку Catalog Draft."""

    async def validate(
        self, tenant_id: UUID, actor_id: UUID, values: CatalogDraftValuesDTO
    ) -> CatalogDraftCheckDTO:
        """Возвращает предметные ошибки preview без записи товара."""
        ...

    async def create(
        self, tenant_id: UUID, actor_id: UUID, values: CatalogDraftValuesDTO
    ) -> UUID:
        """Создаёт заполненный Draft без самостоятельного commit."""
        ...
