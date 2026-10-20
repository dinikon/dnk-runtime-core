from src.modules.channels.application.publication_import.command.start_publication_import.command import (
    StartPublicationImportCommand,
)
from src.modules.channels.application.publication_import.command.start_publication_import.dto import (
    StartPublicationImportResultDTO,
)
from src.modules.channels.application.publication_import.port.jobs import (
    PublicationImportJobsPort,
)
from src.modules.channels.application.product_representation.port.publication_catalog import (
    PublicationCatalogSourcePort,
)
from src.modules.channels.application.product_representation.port.binding_queries import (
    BindingQueriesPort,
)
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.publication_import.repository import (
    PublicationImportRepositoryProtocol,
)
from src.modules.channels.domain.publication_import.aggregate import (
    PublicationImportPreparation,
)
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsNotFoundError,
    ChannelsUnavailableError,
)
from src.modules.channels.domain.product_representation.policy import (
    ensure_linking_allowed,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort


class StartPublicationImportHandler:
    """Создаёт подготовку и оба durable задания без внешних вызовов."""

    def __init__(
        self,
        imports: PublicationImportRepositoryProtocol,
        sources: PublicationCatalogSourcePort,
        channels: ChannelRepositoryProtocol,
        bindings: BindingQueriesPort,
        registry: PluginRegistryProtocol,
        jobs: PublicationImportJobsPort,
        clock: ClockPort,
    ) -> None:
        """Получает необходимые порты общей транзакции."""
        (
            self.imports,
            self.sources,
            self.channels,
            self.bindings,
            self.registry,
            self.jobs,
            self.clock,
        ) = (imports, sources, channels, bindings, registry, jobs, clock)

    async def execute(
        self, command: StartPublicationImportCommand
    ) -> StartPublicationImportResultDTO:
        """Обеспечивает replay запуска без второй подготовки и лишних jobs."""
        await self.imports.lock_request(
            EntityIdVO(command.tenant_id), EntityIdVO(command.preparation_id)
        )
        try:
            existing = await self.imports.get(
                EntityIdVO(command.preparation_id), lock=False
            )
        except ChannelsNotFoundError:
            existing = None
        if existing is not None:
            if (
                existing.publication_id.uuid != command.publication_id
                or existing.actor_id.uuid != command.actor_id
                or existing.observed_revision != command.expected_observed_revision
            ):
                raise ChannelsConflictError("idempotency_key_reused")
            return StartPublicationImportResultDTO(existing.id.uuid)
        source = await self.sources.source(command.publication_id, lock=True)
        ensure_linking_allowed(source.archived)
        if source.observed_revision != command.expected_observed_revision:
            raise ChannelsConflictError("publication_revision_conflict")
        if await self.bindings.active(command.publication_id):
            raise ChannelsConflictError("publication_already_bound")
        channel = await self.channels.get(
            EntityIdVO(source.channel_id), for_update=False
        )
        connection = channel.require_connection()
        if connection.is_paused or connection.verification_status != "verified":
            raise ChannelsConflictError("connection_not_ready")
        if (
            "read_publication_details"
            not in self.registry.manifest(channel.platform_kind).capabilities
        ):
            raise ChannelsUnavailableError("publication_details_unsupported")
        now = self.clock.now()
        preparation = PublicationImportPreparation.create(
            EntityIdVO(command.preparation_id),
            EntityIdVO(command.publication_id),
            EntityIdVO(command.actor_id),
            connection.generation,
            source.observed_revision,
            now,
        )
        await self.imports.add(preparation)
        await self.jobs.prepare(
            command.tenant_id, preparation.id.uuid, preparation.sequence, now
        )
        await self.jobs.cleanup(
            command.tenant_id, preparation.id.uuid, preparation.expires_at
        )
        return StartPublicationImportResultDTO(preparation.id.uuid)
