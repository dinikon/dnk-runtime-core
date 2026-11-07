from src.modules.inventory.domain.policy.stock_movement_balance import (
    StockMovementBalancePolicy,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.error import (
    StockMovementValuationSourceError,
)
from src.modules.inventory.domain.stock_posting.movement_valuation_snapshot import (
    StockMovementValuationSnapshot,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.stock_posting.value_object.movement_entry_pair import (
    StockMovementEntryPairVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO


class StockMovementValuationPolicy:
    """Выделяет основание переноса стоимости одной пары из полностью проверенного внутреннего перемещения."""

    @staticmethod
    def build_snapshot(
        *,
        posting: StockPostingSnapshot,
        pair: StockMovementEntryPairVO,
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
    ) -> StockMovementValuationSnapshot:
        """Повторно проверяет весь баланс, затем полные стороны выбранной пары без новых коэффициентов и текущих остатков."""
        if (
            not isinstance(posting, StockPostingSnapshot)
            or not isinstance(pair, StockMovementEntryPairVO)
            or not isinstance(positions, tuple)
            or not isinstance(locations, tuple)
        ):
            raise StockMovementValuationSourceError(
                "Нужны снимок проведения, номинальная пара и tuple позиций/локаций."
            )
        posting.ensure_valid()
        pair.ensure_valid()
        if (
            posting.operation_type is not StockOperationType.INTERNAL_MOVE
            or posting.reversal_of_id is not None
        ):
            raise StockMovementValuationSourceError(
                "Основание переноса строится только по обычному INTERNAL_MOVE без компенсации."
            )
        StockMovementBalancePolicy.ensure_balanced(
            entries=posting.entries, positions=positions, locations=locations
        )
        entries = {entry.id: entry for entry in posting.entries}
        outgoing = entries.get(pair.outgoing_entry_id)
        incoming = entries.get(pair.incoming_entry_id)
        if (
            outgoing is None
            or incoming is None
            or outgoing.quantity_delta.value >= 0
            or incoming.quantity_delta.value <= 0
        ):
            raise StockMovementValuationSourceError(
                "Пара должна выбирать существующие отрицательную и положительную записи этого проведения."
            )
        quantity = QuantityVO(outgoing.quantity_delta.value.copy_abs())
        if quantity.value != incoming.quantity_delta.value:
            raise StockMovementValuationSourceError(
                "Первый срез требует полные стороны пары с одинаковым количеством."
            )
        by_position = {position.id: position for position in positions}
        by_location = {location.id: location for location in locations}
        source = by_position[outgoing.position_id]
        target = by_position[incoming.position_id]
        snapshot = StockMovementValuationSnapshot(
            posting.id,
            pair,
            source,
            target,
            by_location[source.dimensions.location_id].warehouse_id,
            quantity,
            posting.posted_at,
        )
        snapshot.ensure_valid()
        return snapshot
