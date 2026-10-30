from uuid import UUID
from src.modules.channels.application.content_delivery.cancellation import (
    ContentDeliveryCancellation,
)

from src.modules.channels.application.catalog_binding.ports import BindingCatalogPort
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.application.product_representation.service.reader import (
    RepresentationContext,
    RepresentationReader,
)
from src.modules.channels.application.product_representation.service.drafts import (
    RepresentationDrafts,
)
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError
from src.modules.channels.domain.catalog_binding.repository import (
    CatalogBindingRepository,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.product_representation.aggregate import (
    ProductRepresentation,
)
from src.modules.channels.domain.product_representation.error import (
    ProductRepresentationError,
)
from src.modules.channels.domain.product_representation.overrides import (
    RepresentationOverridesVO,
)
from src.modules.channels.domain.product_representation.repository import (
    ProductRepresentationRepositoryProtocol,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class RepresentationWrites:
    """Координирует команды и общий порядок блокировок без вложенных handlers/UoW."""

    def __init__(
        self,
        *,
        reader: RepresentationReader,
        drafts: RepresentationDrafts,
        catalog: BindingCatalogPort,
        channels: ChannelRepositoryProtocol,
        groups: CatalogBindingRepository,
        representations: ProductRepresentationRepositoryProtocol,
        uuid: UUIdGeneratorProtocol,
        clock: ClockPort,
        cancellations: ContentDeliveryCancellation,
    ) -> None:
        """Принимает порты одной tenant-транзакции и генераторы внешней сборки."""
        self._reader = reader
        self._drafts = drafts
        self._catalog = catalog
        self._channels = channels
        self._groups = groups
        self._representations = representations
        self._uuid = uuid
        self._clock = clock
        self._cancellations = cancellations

    async def lock_context(
        self, *, tenant_id: UUID, channel_id: UUID, group_id: UUID
    ) -> tuple[RepresentationContext, ProductRepresentation | None]:
        """Блокирует Catalog → Channel → группу → representation и перечитывает контекст."""
        before = await self._reader.load(channel_id=channel_id, group_id=group_id)
        await self._catalog.lock(tenant_id, before.binding.catalog_root_id)
        channel = await self._channels.get(EntityIdVO(channel_id), for_update=True)
        if channel is None:
            raise CatalogBindingError("channel_not_found")
        group = await self._groups.get(
            channel.connection.id, EntityIdVO(group_id), for_update=True
        )
        if group is None:
            raise CatalogBindingError("binding_not_found")
        representation = await self._representations.get(group.id)
        return (
            await self._reader.load(channel_id=channel_id, group_id=group_id),
            representation,
        )

    async def save(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        group_id: UUID,
        actor_id: UUID,
        expected_revision: int,
        expected_binding_revision: int,
        expected_config_revision: int,
        overrides: RepresentationOverridesVO,
    ) -> RepresentationContext:
        """Сохраняет полный документ; неготовый допустимый черновик выключает экспорт."""
        context, representation = await self.lock_context(
            tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
        )
        self._reader.require_context(
            context,
            expected_revision=expected_revision,
            expected_binding_revision=expected_binding_revision,
            expected_config_revision=expected_config_revision,
        )
        now = self._clock.now()
        draft = await self._drafts.prepare(
            context=context, overrides=overrides, as_of=now, for_update=True
        )
        if draft.unavailable_files:
            raise ChannelInputError(
                "representation_image_unavailable", field="overrides"
            )
        if representation is None:
            representation = ProductRepresentation.create(
                identifier=EntityIdVO(self._uuid.new()),
                binding_group_id=EntityIdVO(group_id),
                overrides=draft.overrides,
                actor=EntityIdVO(actor_id),
                now=now,
            )
        else:
            representation.change_overrides(
                overrides=draft.overrides,
                expected_revision=expected_revision,
                export_ready=not draft.export_blockers,
                actor=EntityIdVO(actor_id),
                now=now,
            )
        await self._representations.save(representation)
        if not representation.export_enabled:
            await self._cancellations.cancel(representation.id)
        return await self._reader.load(channel_id=channel_id, group_id=group_id)

    async def enable(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        group_id: UUID,
        actor_id: UUID,
        expected_revision: int,
        expected_binding_revision: int,
        expected_config_revision: int,
    ) -> RepresentationContext:
        """Повторно проверяет все локали и файлы перед отдельным разрешением экспорта."""
        context, representation = await self.lock_context(
            tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
        )
        self._reader.require_context(
            context,
            expected_revision=expected_revision,
            expected_binding_revision=expected_binding_revision,
            expected_config_revision=expected_config_revision,
        )
        if representation is None:
            raise ProductRepresentationError("representation_not_saved", conflict=True)
        now = self._clock.now()
        draft = await self._drafts.prepare(
            context=context,
            overrides=representation.overrides,
            as_of=now,
            for_update=True,
        )
        representation.enable_export(
            expected_revision=expected_revision,
            blockers=draft.export_blockers,
            actor=EntityIdVO(actor_id),
            now=now,
        )
        await self._representations.save(representation)
        return await self._reader.load(channel_id=channel_id, group_id=group_id)

    async def disable(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        group_id: UUID,
        actor_id: UUID,
        expected_revision: int,
        expected_binding_revision: int,
        expected_config_revision: int,
    ) -> RepresentationContext:
        """Идемпотентно выключает разрешение, не создавая запись для defaults."""
        context, representation = await self.lock_context(
            tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
        )
        self._reader.require_context(
            context,
            expected_revision=expected_revision,
            expected_binding_revision=expected_binding_revision,
            expected_config_revision=expected_config_revision,
        )
        if representation is not None:
            representation.disable_export(
                expected_revision=expected_revision,
                actor=EntityIdVO(actor_id),
                now=self._clock.now(),
            )
            await self._representations.save(representation)
            await self._cancellations.cancel(representation.id)
        return await self._reader.load(channel_id=channel_id, group_id=group_id)
