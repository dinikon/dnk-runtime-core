from dataclasses import dataclass
from datetime import datetime
from collections.abc import Callable
from uuid import UUID
from decimal import Decimal

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


class StockPlanning:
    """Собирает факты из публичных портов; решения оставляет Domain policy."""

    def __init__(
        self,
        bindings: BindingReadPort,
        catalog: BindingCatalogPort,
        read: StockReadPort,
    ) -> None:
        """Все порты читают один tenant в текущем UoW."""
        self.bindings, self.catalog, self.read = bindings, catalog, read

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
            for pair in group.items:
                publication, position = publications.get(
                    pair.publication_id
                ), positions.get(pair.catalog_position_id)
                if publication is None or position is None:
                    continue
                parent = publications.get(publication.lookup.parent_id)
                shared = publication.stock_mode == "parent" or (
                    group.platform == "woocommerce"
                    and publication.stock_mode == "untracked"
                    and parent is not None
                    and parent.stock_mode == "own"
                )
                owner = parent if shared else publication
                if owner is None:
                    continue
                quantity = (
                    Decimal(position.quantity)
                    if position.quantity is not None
                    else None
                )
                # Catalog хранит целые количества; проверка сохраняет неизвестное значение.
                if quantity is not None and quantity != quantity.to_integral_value():
                    raise StockSyncError("stock_quantity_invalid")
                facts = StockLinkFacts(
                    EntityIdVO(publication.lookup.id),
                    EntityIdVO(owner.lookup.id),
                    EntityIdVO(position.id),
                    EntityIdVO(position.stock_source_id),
                    int(quantity) if quantity is not None else None,
                    position.backorders,
                    owner.write_target_key,
                )
                result.append(StockPlanItem(group, publication, owner, facts))
        return tuple(result)

    @staticmethod
    def ensure_exportable(
        selected: StockPlanItem, items: tuple[StockPlanItem, ...]
    ) -> None:
        """Не допускает неподдержанную топологию даже при одинаковых количествах."""
        StockOwnershipPolicy().ensure_exportable(
            selected.facts, tuple(v.facts for v in items)
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
        """Сохраняет весь выбранный набор атомарно, без частичных заданий при отказе."""
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
        ids = set(publication_ids)
        if len(ids) != len(publication_ids) or ids - {
            v.publication.lookup.id for v in group_items
        }:
            raise StockSyncError("stock_selection_invalid")
        selected = tuple(
            v for v in group_items if not ids or v.publication.lookup.id in ids
        )
        if direction == "write" and not automatic:
            for item in selected:
                self.planning.ensure_exportable(item, all_items)
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
            operation_id = self.uuid()
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
            await self.jobs.schedule(
                tenant_id=tenant_id, channel_id=channel.id.uuid, state=state, now=now
            )
            operations.append(operation_id)
        return tuple(operations)
