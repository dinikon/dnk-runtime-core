from datetime import datetime

from src.modules.inventory.domain.policy.stock_movement_valuation import (
    StockMovementValuationPolicy,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.valuation_layer.basis_snapshot import (
    ValuationLayerBasisSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import ValuationLayerTimeError
from src.modules.inventory.domain.valuation_layer.movement_consumption_snapshot import (
    ValuationLayerMovementConsumptionSnapshot,
)
from src.modules.inventory.domain.valuation_posting.entity.valuation_entry import (
    ValuationEntry,
)
from src.modules.inventory.domain.valuation_posting.error import (
    DuplicateValuationEntryError,
    ValuationPostingSourceError,
    ValuationPostingTimeError,
)
from src.modules.inventory.domain.valuation_posting.time import (
    normalize_valuation_posting_time,
)
from src.modules.inventory.domain.valuation_posting.value_object.entry_binding import (
    ValuationEntryBindingVO,
)
from src.modules.shared.domain.value_object.money import MoneyVO


class StockMovementValuationPostingPolicy:
    """Регистрирует стоимость полной пары INTERNAL_MOVE по исходному и производному основаниям."""

    @staticmethod
    def build_entries(
        *,
        posting: StockPostingSnapshot,
        consumption: ValuationLayerMovementConsumptionSnapshot,
        destination: ValuationLayerBasisSnapshot,
        entry_bindings: tuple[ValuationEntryBindingVO, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        posted_at: datetime,
    ) -> tuple[ValuationEntry, ValuationEntry]:
        """Сверяет полное покрытие Ledger и формирует сначала выбытие, затем поступление стоимости."""
        if (
            not isinstance(consumption, ValuationLayerMovementConsumptionSnapshot)
            or not isinstance(destination, ValuationLayerBasisSnapshot)
            or not isinstance(entry_bindings, tuple)
        ):
            raise ValuationPostingSourceError(
                "Нужны снимки потребления и слоя назначения и tuple привязок."
            )
        destination.ensure_valid()
        if destination.transfer_origin is None:
            raise ValuationPostingSourceError(
                "Для поступления стоимости нужен слой, образованный переносом."
            )
        try:
            expected_destination = consumption.destination_basis(
                identifier=destination.id, created_at=destination.created_at
            )
        except ValuationLayerTimeError as exc:
            raise ValuationPostingTimeError(
                "Нужна согласованная хронология потребления и создания слоя назначения."
            ) from exc
        movement = StockMovementValuationPolicy.build_snapshot(
            posting=posting,
            pair=consumption.movement.pair,
            positions=positions,
            locations=locations,
        )
        if len(posting.entries) != 2 or movement != consumption.movement:
            raise ValuationPostingSourceError(
                "Результат потребления должен покрывать единственную полную пару этого проведения."
            )
        if destination != expected_destination:
            raise ValuationPostingSourceError(
                "Исходная оценка и происхождение слоя назначения должны соответствовать переносу."
            )
        at = normalize_valuation_posting_time(posted_at)
        if at < destination.created_at:
            raise ValuationPostingTimeError(
                "Журнал стоимости нельзя зарегистрировать раньше создания слоя назначения."
            )

        source = consumption.layer
        bindings_by_layer = {}
        entry_ids = set()
        for binding in entry_bindings:
            if not isinstance(binding, ValuationEntryBindingVO):
                raise ValuationPostingSourceError(
                    "Нужны номинальные привязки ID записей стоимости к слоям."
                )
            binding.ensure_valid()
            if binding.layer_id in bindings_by_layer or binding.entry_id in entry_ids:
                raise DuplicateValuationEntryError(
                    "Слои и ID записей привязок не должны повторяться."
                )
            bindings_by_layer[binding.layer_id] = binding.entry_id
            entry_ids.add(binding.entry_id)
        if set(bindings_by_layer) != {source.id, destination.id}:
            raise ValuationPostingSourceError(
                "Перенос требует ровно по одной привязке для каждого из двух слоёв."
            )

        ledger = {entry.id: entry for entry in posting.entries}
        cost = destination.cost_basis.total_cost
        outgoing, incoming = (
            ValuationEntry.create(
                identifier=bindings_by_layer[layer.id],
                ledger_entry_id=entry_id,
                position_id=ledger[entry_id].position_id,
                layer_id=layer.id,
                inventory_item_id=layer.inventory_item_id,
                owner_id=layer.owner_id,
                warehouse_id=layer.warehouse_id,
                base_uom=layer.base_uom,
                quantity_delta=ledger[entry_id].quantity_delta,
                cost_delta=delta,
            )
            for layer, entry_id, delta in (
                (
                    source,
                    movement.pair.outgoing_entry_id,
                    MoneyVO(cost.amount.copy_negate(), cost.currency),
                ),
                (destination, movement.pair.incoming_entry_id, cost),
            )
        )
        return outgoing, incoming
