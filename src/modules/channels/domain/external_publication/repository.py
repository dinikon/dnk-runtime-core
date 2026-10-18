from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
)


class ExternalPublicationRepositoryProtocol(Protocol):
    """Хранит observed агрегаты, не обращаясь к Catalog."""

    async def find(
        self, connection_id: EntityIdVO, resource_type: str, external_id: str
    ) -> ExternalPublication | None:
        """Находит существующее наблюдение по стабильной identity."""
        ...

    async def add(self, publication: ExternalPublication) -> None:
        """Добавляет первое наблюдение без commit."""
        ...

    async def save(self, publication: ExternalPublication) -> None:
        """Сохраняет новое наблюдение без commit."""
        ...
