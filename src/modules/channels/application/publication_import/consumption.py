from dataclasses import replace
from uuid import UUID
from src.modules.channels.application.product_representation.contracts import (
    CatalogDraftValuesDTO,
    CatalogDraftImageDTO,
    PublicationCatalogSourceDTO,
)
from src.modules.channels.domain.publication_import.repository import (
    PublicationImportRepositoryProtocol,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsValidationError,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort


class PublicationImportConsumptionService:
    """Передаёт подтверждённое содержимое подготовки общему созданию Catalog."""

    def __init__(
        self,
        imports: PublicationImportRepositoryProtocol,
        channels: ChannelRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Получает порты того же UoW, что товар, связь и receipt."""
        self.imports, self.channels, self.clock = imports, channels, clock

    async def consume(
        self,
        source: PublicationCatalogSourceDTO,
        actor_id: UUID,
        identifier: UUID,
        expected_revision: int,
        values: CatalogDraftValuesDTO,
    ) -> CatalogDraftValuesDTO:
        """Проверяет владение, версию ресурса и выбранные фото без доверия file_id клиента."""
        preparation = await self.imports.get(EntityIdVO(identifier))
        if (
            preparation.publication_id.uuid != source.publication_id
            or preparation.actor_id.uuid != actor_id
            or preparation.observed_revision != source.observed_revision
        ):
            raise ChannelsConflictError("import_preparation_source_mismatch")
        channel = await self.channels.get(
            EntityIdVO(source.channel_id), for_update=False
        )
        connection = channel.require_connection()
        if (
            connection.is_paused
            or connection.verification_status != "verified"
            or connection.generation != preparation.connection_generation
        ):
            raise ChannelsConflictError("import_source_changed")
        snapshot = preparation.snapshot
        if (
            snapshot is None
            or set(values.titles) != set(snapshot.translations)
            or set(values.descriptions) != set(snapshot.translations)
        ):
            raise ChannelsValidationError("publication_locales_mismatch")
        if (bool(values.gallery) != (values.primary_image_id is not None)) or (
            values.gallery and values.primary_image_id not in values.gallery
        ):
            raise ChannelsValidationError("invalid_import_primary_image")
        preparation.consume(expected_revision, values.gallery, self.clock.now())
        images = {image.id: image for image in snapshot.images}
        resolved = tuple(
            CatalogDraftImageDTO(
                key, preparation.media[key].file_id.uuid, images[key].alt
            )
            for key in values.gallery
        )
        await self.imports.save(preparation)
        return replace(values, image_files=resolved)
