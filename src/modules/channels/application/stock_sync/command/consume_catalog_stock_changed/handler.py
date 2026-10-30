from uuid import UUID

from src.modules.catalog.application.catalog_item.stock_events import (
    CATALOG_STOCK_CHANGED,
)
from src.modules.channels.application.stock_sync.command.consume_catalog_stock_changed.command import (
    ConsumeCatalogStockChangedCommand,
)
from src.modules.channels.application.stock_sync.service import StockOperations
from src.modules.channels.application.catalog_binding.ports import BindingReadPort
from src.modules.shared.application.events.inbox_repository_protocol import (
    InboxRepositoryProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class ConsumeCatalogStockChangedHandler:
    """Inbox и задания назначения фиксируются атомарно в одном UoW."""

    def __init__(
        self,
        *,
        operations: StockOperations,
        bindings: BindingReadPort,
        inbox: InboxRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Не читает Catalog SQL и не вызывает площадки."""
        self.operations, self.bindings, self.inbox, self.clock = (
            operations,
            bindings,
            inbox,
            clock,
        )

    async def execute(self, command: ConsumeCatalogStockChangedCommand) -> None:
        """Повторная доставка не создаёт новых поколений отправки."""
        event = command.event
        if (
            event.event_type != CATALOG_STOCK_CHANGED
            or event.event_version != 1
            or event.aggregate_type != "catalog_item"
        ):
            raise ValueError("Invalid Catalog stock event")
        source = "channels.catalog_stock"
        if not await self.inbox.record_received(
            source=source,
            message_id=str(event.event_id),
            event=event,
            received_at=self.clock.now(),
        ):
            return
        positions = {UUID(value) for value in event.payload["position_ids"]}
        groups, _ = await self.bindings.records(
            catalog_root_id=event.aggregate_id, limit=None
        )
        for group in sorted(groups, key=lambda v: (str(v.channel_id), str(v.id))):
            publications = tuple(
                pair.publication_id
                for pair in group.items
                if pair.catalog_position_id in positions
            )
            if not publications:
                continue
            await self.operations.request(
                tenant_id=event.tenant_id,
                channel_id=group.channel_id,
                group_id=group.id,
                direction="write",
                publication_ids=publications,
                now=self.clock.now(),
                automatic=True,
                occurred_at=event.occurred_at,
            )
        await self.inbox.mark_consumed(
            tenant_id=event.tenant_id,
            source=source,
            message_id=str(event.event_id),
            consumed_at=self.clock.now(),
        )
