from src.modules.channels.application.publication_import.command.prepare_publication_import_step.command import (
    PreparePublicationImportStepCommand,
)
from src.modules.channels.application.publication_import.command.prepare_publication_import_step.dto import (
    PreparePublicationImportStepResultDTO,
)
from src.modules.channels.application.publication_import.access import (
    PublicationImportAccess,
)
from src.modules.channels.application.plugin_contract import (
    ResourceSettingsDTO,
    ReadPublicationDetailsInputDTO,
)
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.domain.publication_import.repository import (
    PublicationImportRepositoryProtocol,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort


class PreparePublicationImportStepHandler:
    """Фиксирует допуск сетевого шага и возвращает только необходимые данные."""

    def __init__(
        self,
        access: PublicationImportAccess,
        imports: PublicationImportRepositoryProtocol,
        channels: ChannelRepositoryProtocol,
        registry: PluginRegistryProtocol,
        clock: ClockPort,
    ) -> None:
        """Получает контракты текущего tenant UoW."""
        self.access, self.imports, self.channels, self.registry, self.clock = (
            access,
            imports,
            channels,
            registry,
            clock,
        )

    async def execute(
        self, command: PreparePublicationImportStepCommand
    ) -> PreparePublicationImportStepResultDTO | None:
        """Не держит SQL-транзакцию во время будущего обращения к источнику."""
        preparation, source = await self.access.locked(command.preparation_id)
        if not preparation.begin(command.sequence, self.clock.now()):
            return None
        channel = await self.channels.get(
            EntityIdVO(source.channel_id), for_update=False
        )
        connection = channel.require_connection()
        if (
            source.archived
            or connection.is_paused
            or connection.verification_status != "verified"
            or connection.generation != preparation.connection_generation
            or source.observed_revision != preparation.observed_revision
        ):
            preparation.fail("import_source_changed")
            await self.imports.save(preparation)
            return None
        settings = ResourceSettingsDTO(
            connection.settings.endpoint, connection.settings.options
        )
        references = self.registry.validate(channel.platform_kind, settings, None)
        if not 1 <= len(references.locales) <= 2:
            preparation.fail("publication_locales_unsupported")
            await self.imports.save(preparation)
            return None
        image_id = preparation.pending_image()
        image = (
            next(
                (
                    image
                    for image in preparation.snapshot.images
                    if image.id == image_id
                ),
                None,
            )
            if preparation.snapshot
            else None
        )
        await self.imports.save(preparation)
        return PreparePublicationImportStepResultDTO(
            preparation.id.uuid,
            preparation.actor_id.uuid,
            source.connection_id,
            channel.platform_kind,
            ReadPublicationDetailsInputDTO(
                settings,
                connection.resource_identity,
                source.resource_type,
                source.external_id,
                source.provider_context,
            ),
            references.locales,
            connection.credentials_ciphertext,
            image_id,
            image.url if image else None,
        )
