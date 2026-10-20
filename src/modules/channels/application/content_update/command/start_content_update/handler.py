from datetime import timedelta
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.content_update.command.start_content_update.command import (
    StartContentUpdateCommand,
)
from src.modules.channels.application.content_update.command.start_content_update.dto import (
    StartContentUpdateResultDTO,
)
from src.modules.channels.application.content_update.access import ContentUpdateAccess
from src.modules.channels.application.content_update.port.jobs import ContentUpdateJobs
from src.modules.channels.application.plugin_contract import ResourceSettingsDTO
from src.modules.channels.domain.content_update.aggregate import ContentUpdateRun
from src.modules.channels.domain.content_update.entity.item import ContentUpdateItem
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsValidationError,
    ChannelsUnavailableError,
)


class StartContentUpdateHandler:
    """Создаёт read-only подготовку и durable job в одной транзакции."""

    def __init__(
        self, access: ContentUpdateAccess, jobs: ContentUpdateJobs, clock: ClockPort
    ) -> None:
        """Принимает порты текущего UoW без SQL или HTTP клиентов."""
        self.access, self.jobs, self.clock = access, jobs, clock

    async def execute(
        self, command: StartContentUpdateCommand
    ) -> StartContentUpdateResultDTO:
        """Переиспользует текущие связи и согласованный Catalog snapshot."""
        identifiers = tuple(sorted(command.publication_ids, key=str))
        if not 1 <= len(identifiers) <= 50 or len(set(identifiers)) != len(identifiers):
            raise ChannelsValidationError("invalid_content_update_selection")
        await self.access.runs.lock_request(EntityIdVO(command.run_id))
        channel = await self.access.channels.get(EntityIdVO(command.channel_id))
        await self.access.runs.lock_scope(channel.id)
        if await self.access.runs.exists(EntityIdVO(command.run_id)):
            run = await self.access.runs.get(EntityIdVO(command.run_id))
            run.ensure_owner(EntityIdVO(command.actor_id))
            if (
                run.channel_id != channel.id
                or tuple(item.publication_id.uuid for item in run.items) != identifiers
            ):
                raise ChannelsConflictError("content_update_request_key_reused")
            return StartContentUpdateResultDTO(run.id.uuid)
        connection = channel.ensure_network()
        manifest = self.access.registry.manifest(channel.platform_kind)
        if "preview_content_update" not in manifest.capabilities:
            raise ChannelsUnavailableError("content_update_unsupported")
        references = self.access.registry.validate(
            channel.platform_kind,
            ResourceSettingsDTO(
                connection.settings.endpoint, connection.settings.options
            ),
            None,
        )
        targets = []
        for identifier in identifiers:
            source = await self.access.sources.source(identifier, lock=True)
            binding = await self.access.bindings.active(identifier)
            if (
                source.connection_id != connection.id.uuid
                or binding is None
                or binding.connection_id != connection.id.uuid
            ):
                raise ChannelsConflictError("content_update_binding_required")
            targets.append((source, binding))
        snapshots = await self.access.catalog.snapshot(
            command.tenant_id,
            tuple(binding.catalog_item_id for _, binding in targets),
            references.locales,
        )
        items = [
            ContentUpdateItem.create(
                EntityIdVO(source.publication_id),
                EntityIdVO(binding.catalog_item_id),
                EntityIdVO(binding.binding_id),
                binding.revision,
                source.resource_type,
                source.external_id,
                source.provider_context,
                snapshots[binding.catalog_item_id],
            )
            for source, binding in targets
        ]
        now = self.clock.now()
        run = ContentUpdateRun.create(
            EntityIdVO(command.run_id),
            channel.id,
            connection.id,
            EntityIdVO(command.actor_id),
            connection.generation,
            manifest.sdk_version,
            now,
            now + timedelta(hours=24),
            items,
        )
        await self.access.runs.save(run)
        await self.jobs.content_update(
            command.tenant_id, command.run_id, run.sequence, now
        )
        return StartContentUpdateResultDTO(run.id.uuid)
