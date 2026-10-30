from src.modules.channels.domain.stock_sync.state import DesiredStockVO, StockFeaturesVO
from src.modules.channels.application.port.platform import PlatformRegistry
from dataclasses import dataclass
from datetime import datetime
from collections.abc import Callable
from uuid import UUID

from src.modules.channels.application.catalog_binding.ports import (
    BindingReadPort,
    BindingCatalogPort,
)
from src.modules.channels.application.catalog_binding.contracts import BindingRecord
from src.modules.channels.application.stock_sync.ports import (
    StockReadPort,
    StockJobsPort,
    StockPublication,
)
from src.modules.channels.domain.stock_sync.aggregate import StockSync
from src.modules.channels.domain.stock_sync.error import StockSyncError
from src.modules.channels.domain.stock_sync.repository import (
    StockSyncRepositoryProtocol,
)
from src.modules.channels.domain.stock_sync.value_object import (
    StockDirection,
    StockLinkFacts,
    StockOwnershipPolicy,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class StockPlanItem:
    """Однозначная пара владельцев с якорем существующей группы связей."""

    group: BindingRecord
    publication: StockPublication
    owner: StockPublication
    facts: StockLinkFacts
    desired: DesiredStockVO
    features: StockFeaturesVO


class StockPlanning:
    """Собирает факты из публичных портов; решения оставляет Domain policy."""

    def __init__(
        self,
        bindings: BindingReadPort,
        catalog: BindingCatalogPort,
        read: StockReadPort,
        platforms: PlatformRegistry,
    ) -> None:
        """Все порты читают один tenant в текущем UoW."""
        self.bindings, self.catalog, self.read, self.platforms = (
            bindings,
            catalog,
            read,
            platforms,
        )

    async def connection_items(
        self, connection_id: UUID, now: datetime
    ) -> tuple[StockPlanItem, ...]:
        """Учитывает все группы подключения для проверки конфликтов общего остатка."""
        groups, _ = await self.bindings.records(connection_id=connection_id, limit=None)
        families = {
            v.structure.id: v
            for v in await self.catalog.families(
                tuple({g.catalog_root_id for g in groups}), "uk", now
            )
        }
        publications = {
            v.lookup.id: v
            for v in await self.read.publications(
                connection_id,
                tuple({p.publication_id for g in groups for p in g.items}),
            )
        }
        result = []
        for group in groups:
            family = families.get(group.catalog_root_id)
            if family is None:
                continue
            positions = {v.id: v for v in family.positions}
            pairs = [
                (pair.publication_id, positions.get(pair.catalog_position_id))
                for pair in group.items
            ]
            root = publications.get(group.publication_root_id)
            if root is not None and root.lookup.kind == "variable":
                pairs.insert(0, (root.lookup.id, family.root))
            features = self.platforms.get(group.platform).manifest.stock_features
            for publication_id, position in pairs:
                publication = publications.get(publication_id)
                if publication is None or position is None or position.stock is None:
                    continue
                desired = position.stock
                facts = StockLinkFacts(
                    EntityIdVO(publication.lookup.id),
                    EntityIdVO(publication.lookup.id),
                    EntityIdVO(position.id),
                    EntityIdVO(position.stock_source_id),
                    desired.quantity,
                    desired.backorders,
                    publication.write_target_key,
                )
                result.append(
                    StockPlanItem(
                        group, publication, publication, facts, desired, features
                    )
                )
        return tuple(result)

    @staticmethod
    def ensure_exportable(
        selected: StockPlanItem, items: tuple[StockPlanItem, ...]
    ) -> None:
        """Проверяет возможности адресата и однозначность записи доменными правилами."""
        warning = selected.features.warning(selected.desired)
        if warning:
            raise StockSyncError(warning)
        StockOwnershipPolicy().ensure_exportable(
            selected.facts,
            tuple(v.facts for v in items),
        )


class StockOperations:
    """Планирует ручное получение или отправку без сетевого обращения в транзакции."""

    def __init__(
        self,
        *,
        channels: ChannelRepositoryProtocol,
        states: StockSyncRepositoryProtocol,
        planning: StockPlanning,
        jobs: StockJobsPort,
        uuid: Callable[[], UUID],
    ) -> None:
        """Получает порты общего UoW."""
        self.channels, self.states, self.planning, self.jobs, self.uuid = (
            channels,
            states,
            planning,
            jobs,
            uuid,
        )

    async def request(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        group_id: UUID,
        direction: StockDirection,
        publication_ids: tuple[UUID, ...],
        now: datetime,
        automatic: bool = False,
        occurred_at: datetime | None = None,
    ) -> tuple[UUID, ...]:
        """Атомарно планирует доступных участников семьи или выбранное получение."""
        channel = await self.channels.get(EntityIdVO(channel_id), for_update=True)
        if channel is None:
            if automatic:
                return ()
            raise StockSyncError("channel_not_found")
        if automatic and channel.connection.verification.status != "verified":
            return ()
        channel.require_verified_connection()
        if direction == "write" and not channel.connection.stock_sync.allow_export:
            if automatic:
                return ()
            raise StockSyncError("stock_export_forbidden")
        if (
            automatic
            and occurred_at is not None
            and channel.connection.stock_sync.changed_at is not None
            and occurred_at < channel.connection.stock_sync.changed_at
        ):
            return ()
        all_items = await self.planning.connection_items(
            channel.connection.id.uuid, now
        )
        group_items = tuple(
            v
            for v in all_items
            if v.group.id == group_id
            and (
                not automatic
                or occurred_at is None
                or v.group.created_at <= occurred_at
            )
        )
        if not group_items and automatic:
            return ()
        if not group_items:
            raise StockSyncError("stock_binding_not_found")
        for item in group_items:
            pending = await self.states.get(EntityIdVO(item.publication.lookup.id))
            if (
                pending is not None
                and pending.status in {"queued", "running"}
                and pending.direction != direction
                and await self.jobs.active(
                    tenant_id=tenant_id, job_id=pending.operation_id.uuid
                )
            ):
                raise StockSyncError("stock_operation_in_progress")
        ids = set(publication_ids) if direction == "read" else set()
        if direction == "read" and (
            len(ids) != len(publication_ids)
            or ids - {v.publication.lookup.id for v in group_items}
        ):
            raise StockSyncError("stock_selection_invalid")
        selected = tuple(
            v for v in group_items if not ids or v.publication.lookup.id in ids
        )
        if direction == "write":
            exportable = []
            for item in selected:
                try:
                    self.planning.ensure_exportable(item, all_items)
                except StockSyncError:
                    continue
                exportable.append(item)
            selected = tuple(exportable)
            active = []
            for item in selected:
                previous = await self.states.get(EntityIdVO(item.publication.lookup.id))
                if previous is not None and previous.status in {"queued", "running"}:
                    if (
                        previous.direction == direction
                        and previous.config_revision
                        == channel.connection.config_revision
                        and previous.policy_revision
                        == channel.connection.stock_sync.revision
                        and previous.binding_revision == item.group.revision
                        and await self.jobs.active(
                            tenant_id=tenant_id, job_id=previous.operation_id.uuid
                        )
                    ):
                        active.append(previous.operation_id.uuid)
            if active:
                return tuple(dict.fromkeys(active))
        family_operation = self.uuid() if direction == "write" else None
        operations = []
        seen: set[UUID] = set()
        for item in selected:
            owner_id = item.owner.lookup.id
            if owner_id in seen:
                continue
            seen.add(owner_id)
            state = await self.states.get(EntityIdVO(owner_id))
            if (
                state is not None
                and state.status in {"queued", "running"}
                and state.direction == direction
                and state.config_revision == channel.connection.config_revision
                and state.policy_revision == channel.connection.stock_sync.revision
                and state.binding_revision == item.group.revision
                and state.binding_group_id.uuid == group_id
                and await self.jobs.active(
                    tenant_id=tenant_id, job_id=state.operation_id.uuid
                )
            ):
                operations.append(state.operation_id.uuid)
                continue
            operation_id = family_operation or self.uuid()
            if state is None:
                state = StockSync.create(
                    publication_id=EntityIdVO(owner_id),
                    connection_id=channel.connection.id,
                    operation_id=EntityIdVO(operation_id),
                    direction=direction,
                    config_revision=channel.connection.config_revision,
                    policy_revision=channel.connection.stock_sync.revision,
                    binding_group_id=EntityIdVO(group_id),
                    binding_revision=item.group.revision,
                    now=now,
                )
            else:
                state.request(
                    operation_id=EntityIdVO(operation_id),
                    direction=direction,
                    config_revision=channel.connection.config_revision,
                    policy_revision=channel.connection.stock_sync.revision,
                    binding_group_id=EntityIdVO(group_id),
                    binding_revision=item.group.revision,
                    now=now,
                )
            await self.states.save(state)
            if not operations or direction == "read":
                await self.jobs.schedule(
                    tenant_id=tenant_id,
                    channel_id=channel.id.uuid,
                    state=state,
                    now=now,
                )
            operations.append(operation_id)
        return tuple(dict.fromkeys(operations))
