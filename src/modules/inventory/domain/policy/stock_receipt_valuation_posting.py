from datetime import datetime

from src.modules.inventory.domain.policy.stock_posting import StockPostingPolicy
from src.modules.inventory.domain.policy.stock_receipt_valuation import (
    StockReceiptValuationPolicy,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.valuation_layer.receipt_snapshot import (
    ValuationLayerReceiptSnapshot,
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
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO


class StockReceiptValuationPostingPolicy:
    """Строит полную стоимостную регистрацию прихода по снимкам первоначальных слоёв."""

    @staticmethod
    def build_entries(
        *,
        posting: StockPostingSnapshot,
        layers: tuple[ValuationLayerReceiptSnapshot, ...],
        entry_bindings: tuple[ValuationEntryBindingVO, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        posted_at: datetime,
    ) -> tuple[ValuationEntry, ...]:
        """Требует взаимно однозначное полное покрытие Ledger слоями, проверяет основания и сохраняет порядок Ledger."""
        if (
            not isinstance(posting, StockPostingSnapshot)
            or not isinstance(layers, tuple)
            or not layers
            or not isinstance(entry_bindings, tuple)
            or not isinstance(positions, tuple)
            or not isinstance(locations, tuple)
        ):
            raise ValuationPostingSourceError(
                "Нужны снимок проведения и tuple слоёв, привязок, позиций и локаций."
            )
        posting.ensure_valid()
        if (
            posting.operation_type is not StockOperationType.RECEIPT
            or posting.reversal_of_id is not None
        ):
            raise ValuationPostingSourceError(
                "Первоначальная стоимость регистрируется только по обычному RECEIPT."
            )
        at = normalize_valuation_posting_time(posted_at)
        if at < posting.posted_at:
            raise ValuationPostingTimeError(
                "Регистрация стоимости не может предшествовать физическому приходу."
            )
        StockPostingPolicy.ensure_positions(
            entries=posting.entries, positions=positions
        )
        positions_by_id = {position.id: position for position in positions}
        locations_by_id = {}
        for location in locations:
            if not isinstance(location, StockLocationSnapshot):
                raise ValuationPostingSourceError(
                    "Нужны специализированные снимки локаций."
                )
            location.ensure_valid()
            if location.id in locations_by_id:
                raise ValuationPostingSourceError(
                    "Снимки локаций не должны повторяться."
                )
            locations_by_id[location.id] = location
        if set(locations_by_id) != {
            position.dimensions.location_id for position in positions
        }:
            raise ValuationPostingSourceError(
                "Нужны ровно локации исходных позиций без пропусков и лишних снимков."
            )

        layers_by_entry = {}
        layer_ids = set()
        for layer in layers:
            if not isinstance(layer, ValuationLayerReceiptSnapshot):
                raise ValuationPostingSourceError(
                    "Нужны снимки первоначальной стоимости, а не агрегаты слоёв."
                )
            layer.ensure_valid()
            if layer.id in layer_ids or layer.source.ledger_entry_id in layers_by_entry:
                raise DuplicateValuationEntryError(
                    "Слои и исходные записи Ledger не должны повторяться."
                )
            if layer.source.posting_id != posting.id:
                raise ValuationPostingSourceError(
                    "Слой принадлежит другому физическому проведению."
                )
            if at < layer.created_at:
                raise ValuationPostingTimeError(
                    "Регистрация стоимости не может предшествовать созданию слоя."
                )
            layer_ids.add(layer.id)
            layers_by_entry[layer.source.ledger_entry_id] = layer
        if set(layers_by_entry) != {entry.id for entry in posting.entries}:
            raise ValuationPostingSourceError(
                "Каждая запись прихода должна иметь ровно один слой без лишних оснований."
            )

        bindings_by_layer = {}
        entry_ids = set()
        for binding in entry_bindings:
            if not isinstance(binding, ValuationEntryBindingVO):
                raise ValuationPostingSourceError(
                    "Нужны типизированные привязки идентификаторов записей."
                )
            binding.ensure_valid()
            if binding.layer_id in bindings_by_layer or binding.entry_id in entry_ids:
                raise DuplicateValuationEntryError(
                    "Слои и ID записей привязок не должны повторяться."
                )
            bindings_by_layer[binding.layer_id] = binding
            entry_ids.add(binding.entry_id)
        if set(bindings_by_layer) != layer_ids:
            raise ValuationPostingSourceError(
                "Каждому слою нужна одна привязка без лишних идентификаторов."
            )

        entries = []
        for ledger_entry in posting.entries:
            layer = layers_by_entry[ledger_entry.id]
            position = positions_by_id[ledger_entry.position_id]
            receipt = StockReceiptValuationPolicy.build_snapshot(
                posting=posting,
                ledger_entry_id=ledger_entry.id,
                position=position,
                location=locations_by_id[position.dimensions.location_id],
            )
            if (
                layer.source.position_id,
                layer.inventory_item_id,
                layer.owner_id,
                layer.warehouse_id,
                layer.base_uom,
                layer.cost_basis.quantity,
                layer.received_at,
            ) != (
                receipt.position_id,
                receipt.inventory_item_id,
                receipt.owner_id,
                receipt.warehouse_id,
                receipt.base_uom,
                receipt.quantity,
                receipt.received_at,
            ):
                raise ValuationPostingSourceError(
                    "Первоначальное основание слоя не соответствует проверенной записи прихода."
                )
            entries.append(
                ValuationEntry.create(
                    identifier=bindings_by_layer[layer.id].entry_id,
                    ledger_entry_id=ledger_entry.id,
                    position_id=receipt.position_id,
                    layer_id=layer.id,
                    inventory_item_id=receipt.inventory_item_id,
                    owner_id=receipt.owner_id,
                    warehouse_id=receipt.warehouse_id,
                    base_uom=receipt.base_uom,
                    quantity_delta=StockDeltaVO(layer.cost_basis.quantity.value),
                    cost_delta=layer.cost_basis.total_cost,
                )
            )
        return tuple(entries)
