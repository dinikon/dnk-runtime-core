from src.modules.channels.application.stock_sync.query.get_binding_stock.query import (
    GetBindingStockQuery,
)
from src.modules.channels.application.stock_sync.query.get_binding_stock.dto import (
    GetBindingStockResultDTO,
    BindingStockItemDTO,
)
from src.modules.channels.application.stock_sync.service import StockPlanning
from src.modules.channels.application.stock_sync.ports import StockReadPort
from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepository,
)
from src.modules.channels.domain.stock_sync.error import StockSyncError
from src.modules.shared.domain.time.clock_port import ClockPort


class GetBindingStockHandler:
    """Читает проекции и вычисляет доступность действий без восстановления агрегатов."""

    def __init__(
        self,
        *,
        channels: ChannelQueryRepository,
        planning: StockPlanning,
        read: StockReadPort,
        clock: ClockPort,
    ) -> None:
        """Получает read порты текущего tenant."""
        self.channels, self.planning, self.read, self.clock = (
            channels,
            planning,
            read,
            clock,
        )

    async def execute(self, query: GetBindingStockQuery) -> GetBindingStockResultDTO:
        """Возвращает конкретные причины блокировки отправки каждой позиции."""
        channel = await self.channels.get(query.channel_id)
        connection = await self.planning.bindings.connection(query.channel_id)
        if channel is None or connection is None:
            raise StockSyncError("channel_not_found")
        plans = await self.planning.connection_items(connection.id, self.clock.now())
        selected = tuple(v for v in plans if v.group.id == query.group_id)
        if not selected:
            raise StockSyncError("stock_binding_not_found")
        states = {
            v.publication_id: v
            for v in await self.read.states(
                connection.id, tuple({v.owner.lookup.id for v in selected})
            )
        }
        items = []
        for plan in selected:
            blocker = None
            try:
                self.planning.ensure_exportable(plan, plans)
            except StockSyncError as exc:
                blocker = exc.code
            if channel.verification.status != "verified":
                blocker = "stock_connection_unverified"
            elif not channel.allow_stock_export:
                blocker = "stock_export_forbidden"
            operation = states.get(plan.owner.lookup.id)
            items.append(
                BindingStockItemDTO(
                    plan.publication.lookup.id,
                    plan.owner.lookup.id,
                    plan.facts.catalog_position_id.uuid,
                    plan.facts.catalog_owner_id.uuid,
                    plan.facts.quantity,
                    plan.owner.quantity,
                    plan.owner.availability,
                    blocker,
                    operation,
                )
            )
        return GetBindingStockResultDTO(channel.allow_stock_export, tuple(items))
