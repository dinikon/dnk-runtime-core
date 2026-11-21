from datetime import datetime
from decimal import Decimal

from src.modules.inventory.domain.policy.stock_issue_valuation import (
    StockIssueValuationPolicy,
)
from src.modules.inventory.domain.policy.stock_posting import StockPostingPolicy
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.valuation_layer.consumption_snapshot import (
    ValuationLayerConsumptionSnapshot,
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
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.shared.domain.value_object.money import MoneyVO


class StockIssueValuationPostingPolicy:
    """Строит полную оценку ISSUE из исторических результатов потребления без изменения слоёв."""

    @staticmethod
    def build_entries(
        *,
        posting: StockPostingSnapshot,
        consumptions: tuple[ValuationLayerConsumptionSnapshot, ...],
        entry_bindings: tuple[ValuationEntryBindingVO, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        posted_at: datetime,
    ) -> tuple[ValuationEntry, ...]:
        """Повторно проверяет результаты, полное покрытие Ledger и исходный контекст, сохраняя порядок записей."""
        if (
            not isinstance(posting, StockPostingSnapshot)
            or not isinstance(consumptions, tuple)
            or not consumptions
            or not isinstance(entry_bindings, tuple)
            or not isinstance(positions, tuple)
            or not isinstance(locations, tuple)
        ):
            raise ValuationPostingSourceError(
                "Нужны снимок проведения и tuple результатов потребления, привязок, позиций и локаций."
            )
        posting.ensure_valid()
        if (
            posting.operation_type is not StockOperationType.ISSUE
            or posting.reversal_of_id is not None
        ):
            raise ValuationPostingSourceError(
                "Расходная стоимость регистрируется только по обычному ISSUE без компенсации."
            )
        at = normalize_valuation_posting_time(posted_at)
        if at < posting.posted_at:
            raise ValuationPostingTimeError(
                "Регистрация стоимости не может предшествовать физическому расходу."
            )
        StockPostingPolicy.ensure_positions(
            entries=posting.entries, positions=positions
        )
        positions_by_id = {position.id: position for position in positions}
        locations_by_id = {}
        for location in locations:
            if not isinstance(location, StockLocationSnapshot):
                raise ValuationPostingSourceError(
                    "Нужны специализированные снимки исходных локаций."
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

        consumptions_by_entry = {}
        layer_ids = set()
        for consumption in consumptions:
            if not isinstance(consumption, ValuationLayerConsumptionSnapshot):
                raise ValuationPostingSourceError(
                    "Нужны специализированные результаты потребления слоя по ISSUE."
                )
            consumption.ensure_valid()
            if consumption.layer.id in layer_ids:
                raise DuplicateValuationEntryError(
                    "Слой может участвовать в проведении только одним итоговым потреблением."
                )
            if consumption.issue.posting_id != posting.id:
                raise ValuationPostingSourceError(
                    "Результат потребления относится к другому физическому проведению."
                )
            if at < consumption.consumed_at:
                raise ValuationPostingTimeError(
                    "Регистрация стоимости не может предшествовать регистрации потребления слоя."
                )
            consumptions_by_entry.setdefault(
                consumption.issue.ledger_entry_id, []
            ).append(consumption)
            layer_ids.add(consumption.layer.id)
        if set(consumptions_by_entry) != {entry.id for entry in posting.entries}:
            raise ValuationPostingSourceError(
                "Каждой записи ISSUE нужна полная группа результатов без лишних оснований."
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
            bindings_by_layer[binding.layer_id] = binding
            entry_ids.add(binding.entry_id)
        if set(bindings_by_layer) != layer_ids:
            raise ValuationPostingSourceError(
                "Каждому использованному слою нужна одна привязка без лишних идентификаторов."
            )

        entries = []
        for ledger_entry in posting.entries:
            position = positions_by_id[ledger_entry.position_id]
            issue = StockIssueValuationPolicy.build_snapshot(
                posting=posting,
                ledger_entry_id=ledger_entry.id,
                position=position,
                location=locations_by_id[position.dimensions.location_id],
            )
            group = sorted(
                consumptions_by_entry[ledger_entry.id],
                key=lambda value: value.layer.id.uuid.int,
            )
            total = QuantityVO(Decimal(0))
            for consumption in group:
                if consumption.issue != issue:
                    raise ValuationPostingSourceError(
                        "Результат потребления не соответствует заново проверенному основанию ISSUE."
                    )
                total = QuantityArithmeticPolicy.add(total, consumption.quantity)
            if total != issue.quantity:
                raise ValuationPostingSourceError(
                    "Сумма частей должна точно равняться полному количеству записи ISSUE."
                )
            for consumption in group:
                entries.append(
                    ValuationEntry.create(
                        identifier=bindings_by_layer[consumption.layer.id].entry_id,
                        ledger_entry_id=issue.ledger_entry_id,
                        position_id=issue.position_id,
                        layer_id=consumption.layer.id,
                        inventory_item_id=issue.inventory_item_id,
                        owner_id=issue.owner_id,
                        warehouse_id=issue.warehouse_id,
                        base_uom=issue.base_uom,
                        quantity_delta=StockDeltaVO(
                            consumption.quantity.value.copy_negate()
                        ),
                        cost_delta=MoneyVO(
                            consumption.cost.amount.copy_negate(),
                            consumption.cost.currency,
                        ),
                    )
                )
        return tuple(entries)
