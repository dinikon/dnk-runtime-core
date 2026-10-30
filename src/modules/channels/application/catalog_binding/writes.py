from datetime import datetime
from uuid import UUID
from src.modules.channels.application.catalog_binding.contracts import BindingPairDTO
from src.modules.channels.application.catalog_binding.ports import BindingCatalogPort
from src.modules.channels.application.catalog_binding.views import BindingViews
from src.modules.channels.domain.catalog_binding.aggregate import CatalogBindingGroup
from src.modules.channels.domain.catalog_binding.entity import CatalogBindingItem
from src.modules.channels.domain.catalog_binding.repository import (
    CatalogBindingRepository,
)
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError
from src.modules.channels.domain.catalog_binding.value_object import BindingMode
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.product_representation.repository import (
    ProductRepresentationRepositoryProtocol,
)


class BindingWrites:
    """Координирует общие блокировки; решения структуры принимает Domain."""

    def __init__(
        self,
        catalog: BindingCatalogPort,
        groups: CatalogBindingRepository,
        channels: ChannelRepositoryProtocol,
        views: BindingViews,
        uuid: UUIdGeneratorProtocol,
        representations: ProductRepresentationRepositoryProtocol,
    ) -> None:
        """Получает порты общего внешнего UoW."""
        self.catalog, self.groups, self.channels, self.views, self.uuid = (
            catalog,
            groups,
            channels,
            views,
            uuid,
        )
        self.representations = representations

    async def create(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        catalog_root_id: UUID,
        mode: BindingMode,
        publication_root_id: UUID | None,
        items: tuple[BindingPairDTO, ...],
        catalog_token: str,
        publication_token: str,
        actor_id: UUID,
        now: datetime,
        locale: str,
    ) -> CatalogBindingGroup:
        """Создаёт группу после блокировки семьи и Channel."""
        await self.catalog.lock(tenant_id, catalog_root_id)
        channel = await self.channels.get(EntityIdVO(channel_id), for_update=True)
        if channel is None:
            raise CatalogBindingError("channel_not_found")
        group = CatalogBindingGroup.create(
            identifier=EntityIdVO(self.uuid.new()),
            connection_id=channel.connection.id,
            catalog_root_id=EntityIdVO(catalog_root_id),
            mode=mode,
            publication_root_id=(
                EntityIdVO(publication_root_id) if publication_root_id else None
            ),
            items=self.items(items, ()),
            actor=EntityIdVO(actor_id),
            now=now,
        )
        await self.validate(
            group,
            channel.platform_kind,
            catalog_token,
            publication_token,
            locale,
            now,
            group.items,
        )
        await self.groups.save(group)
        return group

    async def update(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        group_id: UUID,
        expected_revision: int,
        items: tuple[BindingPairDTO, ...],
        catalog_token: str,
        publication_token: str,
        actor_id: UUID,
        now: datetime,
        locale: str,
    ) -> CatalogBindingGroup:
        """Повторно проверяет группу после захвата блокировок в общем порядке."""
        channel = await self.channels.get(EntityIdVO(channel_id))
        if channel is None:
            raise CatalogBindingError("channel_not_found")
        group = await self.groups.get(channel.connection.id, EntityIdVO(group_id))
        if group is None:
            raise CatalogBindingError("binding_not_found")
        await self.catalog.lock(tenant_id, group.catalog_root_id.uuid)
        channel = await self.channels.get(EntityIdVO(channel_id), for_update=True)
        if channel is None:
            raise CatalogBindingError("channel_not_found")
        group = await self.groups.get(
            channel.connection.id, EntityIdVO(group_id), for_update=True
        )
        if group is None:
            raise CatalogBindingError("binding_not_found")
        group.require_revision(expected_revision)
        proposed_items = self.items(items, group.items)
        await self.validate(
            group,
            channel.platform_kind,
            catalog_token,
            publication_token,
            locale,
            now,
            proposed_items,
        )
        representation = await self.representations.get(group.id)
        previous_revision = group.revision
        group.change_items(
            items=proposed_items,
            expected_revision=expected_revision,
            actor=EntityIdVO(actor_id),
            now=now,
        )
        await self.groups.save(group)
        if representation is not None and group.revision != previous_revision:
            representation.reconcile_binding_items(
                retained_ids=tuple(item.id for item in group.items),
                actor=EntityIdVO(actor_id),
                now=now,
            )
            await self.representations.save(representation)
        return group

    async def delete(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        group_id: UUID,
        expected_revision: int,
    ) -> None:
        """Снимает в том числе конфликтную группу и никогда не удаляет источник."""
        channel = await self.channels.get(EntityIdVO(channel_id))
        if channel is None:
            raise CatalogBindingError("channel_not_found")
        group = await self.groups.get(channel.connection.id, EntityIdVO(group_id))
        if group is None:
            return
        await self.catalog.lock(tenant_id, group.catalog_root_id.uuid)
        channel = await self.channels.get(EntityIdVO(channel_id), for_update=True)
        if channel is None:
            raise CatalogBindingError("channel_not_found")
        group = await self.groups.get(channel.connection.id, EntityIdVO(group_id))
        if group is None:
            return
        group.require_revision(expected_revision)
        await self.groups.delete(group)

    def items(
        self,
        pairs: tuple[BindingPairDTO, ...],
        previous: tuple[CatalogBindingItem, ...],
    ) -> tuple[CatalogBindingItem, ...]:
        """Сохраняет UUID неизменных пар и создаёт новые Entity явно."""
        old = {(v.catalog_position_id, v.publication_id): v for v in previous}
        return tuple(
            old.get((EntityIdVO(v.catalog_position_id), EntityIdVO(v.publication_id)))
            or CatalogBindingItem.create(
                identifier=EntityIdVO(self.uuid.new()),
                catalog_position_id=EntityIdVO(v.catalog_position_id),
                publication_id=EntityIdVO(v.publication_id),
            )
            for v in pairs
        )

    async def validate(
        self,
        group: CatalogBindingGroup,
        platform: str,
        catalog_token: str,
        publication_token: str,
        locale: str,
        now: datetime,
        proposed_items: tuple[CatalogBindingItem, ...],
    ) -> None:
        """Проверяет структуру и закрепления на актуальных снимках без внешнего API."""
        preview = await self.views.preview(
            connection_id=group.connection_id.uuid,
            platform=platform,
            catalog_root_id=group.catalog_root_id.uuid,
            mode=group.mode,
            publication_root_id=(
                group.publication_root_id.uuid if group.publication_root_id else None
            ),
            items=tuple(
                BindingPairDTO(v.catalog_position_id.uuid, v.publication_id.uuid)
                for v in proposed_items
            ),
            locale=locale,
            now=now,
            group_id=group.id.uuid,
        )
        if (
            preview.catalog_token != catalog_token
            or preview.publication_token != publication_token
        ):
            raise CatalogBindingError("binding_structure_changed", conflict=True)
        if preview.assessment.issues:
            code = preview.assessment.issues[0]
            raise CatalogBindingError(
                code, conflict=code == "binding_publication_occupied"
            )
