from uuid import UUID
from src.modules.channels.domain.product_representation.repository import (
    ProductRepresentationRepositoryProtocol,
)
from src.modules.channels.domain.product_representation.aggregate import (
    ProductRepresentation,
)
from src.modules.channels.application.product_representation.contracts import (
    PublicationCatalogSourceDTO,
    CatalogBindingDTO,
)
from src.modules.channels.domain.error import ChannelsConflictError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class PublicationLinkingService:
    """Разделяет доменное создание связи между bind и create+bind сценариями."""

    def __init__(
        self,
        repository: ProductRepresentationRepositoryProtocol,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Получает порты одного UoW без доступа к SQL."""
        self.repository, self.clock, self.uuid = repository, clock, uuid

    async def attach(
        self,
        source: PublicationCatalogSourceDTO,
        item_id: UUID,
        expected_revision: int | None,
        actor_id: UUID,
    ) -> CatalogBindingDTO:
        """Меняет корень после item/source locks и проверки отсутствия чужой связи."""
        item = await self.repository.find(
            EntityIdVO(source.connection_id), EntityIdVO(item_id)
        )
        if item is not None:
            existing = item.active_binding()
            if existing and existing.publication_id.uuid == source.publication_id:
                return CatalogBindingDTO(
                    existing.id.uuid,
                    item.id.uuid,
                    source.connection_id,
                    source.publication_id,
                    item_id,
                    item.revision,
                    True,
                )
            if expected_revision != item.revision:
                raise ChannelsConflictError("binding_revision_conflict")
        else:
            if expected_revision is not None:
                raise ChannelsConflictError("binding_revision_conflict")
            item = ProductRepresentation.create(
                EntityIdVO(self.uuid.new()),
                EntityIdVO(source.connection_id),
                EntityIdVO(item_id),
            )
        binding = item.bind(
            EntityIdVO(self.uuid.new()),
            EntityIdVO(source.publication_id),
            EntityIdVO(source.connection_id),
            item.revision,
            EntityIdVO(actor_id),
            self.clock.now(),
        )
        await self.repository.save(item)
        return CatalogBindingDTO(
            binding.id.uuid,
            item.id.uuid,
            source.connection_id,
            source.publication_id,
            item_id,
            item.revision,
            True,
        )
