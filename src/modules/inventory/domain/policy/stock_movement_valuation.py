from src.modules.inventory.domain.policy.stock_movement_balance import (
    StockMovementBalancePolicy,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.entity.stock_ledger_entry import (
    StockLedgerEntry,
)
from src.modules.inventory.domain.stock_posting.error import (
    StockMovementValuationSourceError,
)
from src.modules.inventory.domain.stock_posting.movement_valuation_snapshot import (
    StockMovementValuationSnapshot,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.movement_entry_pair import (
    StockMovementEntryPairVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class StockMovementValuationPolicy:
    """Выделяет основания выбранных пар из полностью проверенного внутреннего перемещения."""

    @staticmethod
    def build_snapshot(
        *,
        posting: StockPostingSnapshot,
        pair: StockMovementEntryPairVO,
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
    ) -> StockMovementValuationSnapshot:
        """Повторно проверяет весь баланс, затем полные стороны выбранной пары без новых коэффициентов и текущих остатков."""
        return StockMovementValuationPolicy.build_snapshots(
            posting=posting, pairs=(pair,), positions=positions, locations=locations
        )[0]

    @staticmethod
    def build_snapshots(
        *,
        posting: StockPostingSnapshot,
        pairs: tuple[StockMovementEntryPairVO, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
    ) -> tuple[StockMovementValuationSnapshot, ...]:
        """Проверяет физический контекст один раз и выводит основания явных пар в заданном порядке."""
        if (
            not isinstance(posting, StockPostingSnapshot)
            or not isinstance(pairs, tuple)
            or not pairs
            or any(not isinstance(pair, StockMovementEntryPairVO) for pair in pairs)
            or not isinstance(positions, tuple)
            or not isinstance(locations, tuple)
        ):
            raise StockMovementValuationSourceError(
                "Нужны снимок проведения, непустой tuple номинальных пар и tuple позиций/локаций."
            )
        posting.ensure_valid()
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
        by_position = {position.id: position for position in positions}
        warehouse_id = locations[0].warehouse_id
        return tuple(
            StockMovementValuationPolicy._build_pair_snapshot(
                posting=posting,
                pair=pair,
                entries=entries,
                positions=by_position,
                warehouse_id=warehouse_id,
            )
            for pair in pairs
        )

    @staticmethod
    def _build_pair_snapshot(
        *,
        posting: StockPostingSnapshot,
        pair: StockMovementEntryPairVO,
        entries: dict[StockLedgerEntryIdVO, StockLedgerEntry],
        positions: dict[StockPositionIdVO, StockPositionSnapshot],
        warehouse_id: WarehouseIdVO,
    ) -> StockMovementValuationSnapshot:
        """Сверяет знаки и количество пары на предварительно проверенном физическом контексте."""
        pair.ensure_valid()
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
                "Перенос требует полные стороны пары с одинаковым количеством."
            )
        snapshot = StockMovementValuationSnapshot(
            posting.id,
            pair,
            positions[outgoing.position_id],
            positions[incoming.position_id],
            warehouse_id,
            quantity,
            posting.posted_at,
        )
        snapshot.ensure_valid()
        return snapshot
