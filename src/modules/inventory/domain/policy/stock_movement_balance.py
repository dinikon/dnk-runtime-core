from decimal import Decimal

from src.modules.inventory.domain.policy.stock_posting import StockPostingPolicy
from src.modules.inventory.domain.policy.stock_quantity import StockQuantityPolicy
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.entity.stock_ledger_entry import (
    StockLedgerEntry,
)
from src.modules.inventory.domain.stock_posting.error import (
    InvalidPostingContextError,
    StockMovementBalanceError,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO


class StockMovementBalancePolicy:
    """Проверяет внутреннее перемещение без изменения количества и сохраняемых измерений."""

    @staticmethod
    def ensure_balanced(
        *,
        entries: tuple[StockLedgerEntry, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
    ) -> None:
        """Сверяет адреса одного склада и точный баланс отдельно по каждой комбинации измерений."""
        StockPostingPolicy.ensure_positions(entries=entries, positions=positions)
        if not isinstance(locations, tuple):
            raise InvalidPostingContextError("Нужен tuple снимков локаций перемещения.")
        by_location = {}
        for location in locations:
            if not isinstance(location, StockLocationSnapshot):
                raise InvalidPostingContextError("Нужны снимки локаций перемещения.")
            location.ensure_valid()
            if location.id in by_location:
                raise InvalidPostingContextError(
                    "Локации в контексте не должны повторяться."
                )
            by_location[location.id] = location
        if set(by_location) != {
            position.dimensions.location_id for position in positions
        }:
            raise InvalidPostingContextError(
                "Нужны ровно те локации, на которые ссылаются позиции."
            )
        if len({location.warehouse_id for location in locations}) != 1:
            raise StockMovementBalanceError(
                "Внутреннее перемещение проводится в пределах одного склада."
            )
        by_id = {position.id: position for position in positions}
        groups: dict[tuple[object, ...], list[StockLedgerEntry]] = {}
        for entry in entries:
            dimensions = by_id[entry.position_id].dimensions
            key = (
                dimensions.inventory_item_id,
                dimensions.owner_id,
                dimensions.lot_id,
                dimensions.serial_id,
                dimensions.stock_status,
                entry.base_uom,
            )
            groups.setdefault(key, []).append(entry)
        for group in groups.values():
            quantities = tuple(entry.quantity_delta for entry in group)
            incoming = StockMovementBalancePolicy._total(quantities, negative=False)
            outgoing = StockMovementBalancePolicy._total(quantities, negative=True)
            if incoming != outgoing:
                raise StockMovementBalanceError(
                    "Расход и приход должны совпадать для каждого товара и набора измерений."
                )
            if by_id[
                group[0].position_id
            ].dimensions.serial_id is not None and incoming.value != Decimal(1):
                raise StockMovementBalanceError(
                    "Один экземпляр не может перемещаться одновременно из нескольких позиций."
                )

    @staticmethod
    def _total(deltas: tuple[StockDeltaVO, ...], *, negative: bool) -> QuantityVO:
        """Суммирует модули одной стороны точно, используя общий безопасный механизм арифметики."""
        exponent = min(int(delta.value.as_tuple().exponent) for delta in deltas)
        rules = QuantityRulesVO(Decimal((0, (1,), exponent)))
        total = QuantityVO(Decimal(0))
        for delta in deltas:
            if delta.value.is_signed() is negative:
                total = StockQuantityPolicy.apply_delta(
                    quantity=total,
                    delta=StockDeltaVO(delta.value.copy_abs()),
                    rules=rules,
                )
        return total
