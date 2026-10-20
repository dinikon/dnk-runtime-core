from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from uuid import UUID
from src.modules.channels.domain.publication_import.repository import (
    PublicationImportRepositoryProtocol,
)
from src.modules.channels.domain.publication_import.aggregate import (
    PublicationImportPreparation,
)
from src.modules.channels.application.product_representation.port.publication_catalog import (
    PublicationCatalogSourcePort,
)
from src.modules.channels.application.product_representation.contracts import (
    PublicationCatalogSourceDTO,
)
from src.modules.channels.domain.error import ChannelsConflictError


class PublicationImportAccess:
    """Задаёт единый порядок блокировок: Channel, публикация, подготовка."""

    def __init__(
        self,
        imports: PublicationImportRepositoryProtocol,
        sources: PublicationCatalogSourcePort,
    ) -> None:
        """Получает порты единственной внешней транзакции."""
        self.imports, self.sources = imports, sources

    async def locked(
        self, identifier: UUID, actor_id: UUID | None = None
    ) -> tuple[PublicationImportPreparation, PublicationCatalogSourceDTO]:
        """Разрешает ID без lock, затем блокирует источник перед процессом."""
        probe = await self.imports.get(EntityIdVO(identifier), lock=False)
        source = await self.sources.source(probe.publication_id.uuid, lock=True)
        preparation = await self.imports.get(EntityIdVO(identifier))
        if actor_id is not None and preparation.actor_id.uuid != actor_id:
            raise ChannelsConflictError("import_preparation_actor_mismatch")
        return preparation, source
