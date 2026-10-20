from uuid import UUID
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.content_update.aggregate import ContentUpdateRun
from src.modules.channels.domain.content_update.repository import (
    ContentUpdateRepositoryProtocol,
)
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.application.content_update.port.catalog_content import (
    CatalogContentFacade,
)
from src.modules.channels.application.content_update.port.queries import (
    ContentUpdateQueries,
)
from src.modules.channels.application.product_representation.port.binding_queries import (
    BindingQueriesPort,
)
from src.modules.channels.application.product_representation.port.publication_catalog import (
    PublicationCatalogSourcePort,
)
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsNotFoundError,
    ChannelsUnavailableError,
)


class ContentUpdateAccess:
    """Координирует публичные блокировки владельцев и проверку зафиксированных ссылок."""

    def __init__(
        self,
        runs: ContentUpdateRepositoryProtocol,
        queries: ContentUpdateQueries,
        channels: ChannelRepositoryProtocol,
        bindings: BindingQueriesPort,
        sources: PublicationCatalogSourcePort,
        catalog: CatalogContentFacade,
        registry: PluginRegistryProtocol,
    ) -> None:
        """Получает порты, собранные на одной tenant-транзакции."""
        self.runs, self.queries, self.channels = runs, queries, channels
        self.bindings, self.sources, self.catalog, self.registry = (
            bindings,
            sources,
            catalog,
            registry,
        )

    async def locked(
        self, identifier: UUID, actor_id: UUID | None = None
    ) -> tuple[ContentUpdateRun, Channel]:
        """Блокирует Channel, затем Run; отказ автору не раскрывает чужое содержимое."""
        channel_id, owner_id = await self.queries.scope(identifier)
        if actor_id is not None and owner_id != actor_id:
            raise ChannelsNotFoundError("content_update_not_found")
        channel = await self.channels.get(EntityIdVO(channel_id))
        run = await self.runs.get(EntityIdVO(identifier))
        return run, channel

    async def validate(
        self,
        run: ContentUpdateRun,
        channel: Channel,
        tenant_id: UUID,
        *,
        sending: bool,
        check_content: bool,
    ) -> None:
        """Сверяет generation, ссылки и точные тексты через фасады владельцев."""
        connection = (
            channel.ensure_outbound(run.generation)
            if sending
            else channel.ensure_network(run.generation)
        )
        if connection.id != run.connection_id:
            raise ChannelsConflictError("connection_generation_changed")
        manifest = self.registry.manifest(channel.platform_kind)
        if manifest.sdk_version != run.sdk_version:
            raise ChannelsConflictError("content_update_plugin_changed")
        if sending and "update_content" not in manifest.capabilities:
            raise ChannelsUnavailableError("content_update_write_unsupported")
        for item in run.items:
            source = await self.sources.source(item.publication_id.uuid, lock=True)
            binding = await self.bindings.active(item.publication_id.uuid)
            if (
                source.connection_id != run.connection_id.uuid
                or source.external_id != item.external_id
                or source.resource_type != item.resource_type
                or binding is None
                or binding.binding_id != item.binding_id.uuid
                or binding.revision != item.binding_revision
                or binding.catalog_item_id != item.catalog_item_id.uuid
            ):
                raise ChannelsConflictError("content_update_binding_changed")
        if check_content:
            locales = tuple(text.locale for text in run.items[0].desired.translations)
            snapshots = await self.catalog.snapshot(
                tenant_id,
                tuple(item.catalog_item_id.uuid for item in run.items),
                locales,
            )
            if any(
                snapshots[item.catalog_item_id.uuid].digest() != item.desired.digest()
                for item in run.items
            ):
                raise ChannelsConflictError("catalog_content_changed")
