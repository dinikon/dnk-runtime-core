from datetime import datetime

from src.modules.inventory.domain.policy.stock_movement_valuation import (
    StockMovementValuationPolicy,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.valuation_posting.entity.valuation_entry import (
    ValuationEntry,
)
from src.modules.inventory.domain.valuation_posting.error import (
    DuplicateValuationEntryError,
    ValuationPostingSourceError,
    ValuationPostingTimeError,
)
from src.modules.inventory.domain.valuation_posting.movement_pair_snapshot import (
    ValuationMovementPairSnapshot,
)
from src.modules.inventory.domain.valuation_posting.time import (
    normalize_valuation_posting_time,
)
from src.modules.inventory.domain.valuation_posting.value_object.entry_binding import (
    ValuationEntryBindingVO,
)
from src.modules.shared.domain.value_object.money import MoneyVO


class StockMovementValuationPostingPolicy:
    """Выводит записи стоимости для всех полных пар одного INTERNAL_MOVE."""

    @staticmethod
    def build_entries(
        *,
        posting: StockPostingSnapshot,
        pairs: tuple[ValuationMovementPairSnapshot, ...],
        entry_bindings: tuple[ValuationEntryBindingVO, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        posted_at: datetime,
    ) -> tuple[ValuationEntry, ...]:
        """Требует полного покрытия Ledger и формирует выбытие и поступление каждой пары."""
        if (
            not isinstance(pairs, tuple)
            or not pairs
            or any(
                not isinstance(pair, ValuationMovementPairSnapshot) for pair in pairs
            )
            or not isinstance(entry_bindings, tuple)
        ):
            raise ValuationPostingSourceError(
                "Нужны непустой tuple снимков пар и tuple привязок."
            )
        at = normalize_valuation_posting_time(posted_at)
        for pair in pairs:
            pair.ensure_valid()
            if at < pair.destination.created_at:
                raise ValuationPostingTimeError(
                    "Журнал стоимости нельзя зарегистрировать раньше создания слоя назначения."
                )
        movements = tuple(pair.consumption.movement for pair in pairs)
        physical_movements = StockMovementValuationPolicy.build_snapshots(
            posting=posting,
            pairs=tuple(movement.pair for movement in movements),
            positions=positions,
            locations=locations,
        )
        if physical_movements != movements:
            raise ValuationPostingSourceError(
                "Результаты потребления должны соответствовать физическим парам проведения."
            )
        ledger = {entry.id: entry for entry in posting.entries}
        covered = tuple(
            entry_id
            for movement in movements
            for entry_id in (
                movement.pair.outgoing_entry_id,
                movement.pair.incoming_entry_id,
            )
        )
        if len(set(covered)) != len(covered):
            raise DuplicateValuationEntryError(
                "Каждая запись физического Ledger участвует только в одной паре."
            )
        if set(covered) != set(ledger):
            raise ValuationPostingSourceError(
                "Пары должны покрывать все записи физического Ledger."
            )
        layer_ids = tuple(
            layer_id
            for pair in pairs
            for layer_id in (pair.consumption.layer.id, pair.destination.id)
        )
        if len(set(layer_ids)) != len(layer_ids):
            raise DuplicateValuationEntryError(
                "Слой участвует только в одной записи стоимости перемещения."
            )

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
        if set(bindings_by_layer) != set(layer_ids):
            raise ValuationPostingSourceError(
                "Перенос требует ровно по одной привязке для каждого использованного слоя."
            )

        entries = []
        for pair in pairs:
            movement = pair.consumption.movement
            cost = pair.destination.cost_basis.total_cost
            for layer, entry_id, delta in (
                (
                    pair.consumption.layer,
                    movement.pair.outgoing_entry_id,
                    MoneyVO(cost.amount.copy_negate(), cost.currency),
                ),
                (pair.destination, movement.pair.incoming_entry_id, cost),
            ):
                physical = ledger[entry_id]
                entries.append(
                    ValuationEntry.create(
                        identifier=bindings_by_layer[layer.id],
                        ledger_entry_id=entry_id,
                        position_id=physical.position_id,
                        layer_id=layer.id,
                        inventory_item_id=layer.inventory_item_id,
                        owner_id=layer.owner_id,
                        warehouse_id=layer.warehouse_id,
                        base_uom=layer.base_uom,
                        quantity_delta=physical.quantity_delta,
                        cost_delta=delta,
                    )
                )
        return tuple(entries)
