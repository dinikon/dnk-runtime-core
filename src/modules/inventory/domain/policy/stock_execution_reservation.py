from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionReservationSnapshotError,
)
from src.modules.inventory.domain.stock_execution.reservation_snapshot import (
    StockExecutionReservationSnapshot,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_reservation.consumption_snapshot import (
    StockReservationConsumptionSnapshot,
)
from src.modules.inventory.domain.stock_reservation.error import (
    InvalidReservationConsumptionContextError,
    InvalidReservationExecutionBindingError,
    InvalidStockReservationExecutionSnapshotError,
)
from src.modules.inventory.domain.stock_reservation.execution_snapshot import (
    StockReservationExecutionSnapshot,
)
from src.modules.inventory.domain.stock_reservation.value_object.execution_binding import (
    ReservationExecutionBindingVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class StockExecutionReservationPolicy:
    """Строит погашения резервов из явно назначенных целых строк расхода без изменения агрегатов."""

    @staticmethod
    def build_consumptions(
        *,
        execution: StockExecutionReservationSnapshot,
        bindings: tuple[ReservationExecutionBindingVO, ...],
        reservations: tuple[StockReservationExecutionSnapshot, ...],
    ) -> tuple[StockReservationConsumptionSnapshot, ...]:
        """Проверяет назначение, группирует по резервам и сохраняет ID фактических строк и время факта."""
        if not isinstance(execution, StockExecutionReservationSnapshot):
            raise InvalidStockExecutionReservationSnapshotError(
                "Нужен снимок фактических строк для резервов."
            )
        execution.ensure_valid()
        if execution.operation_type is not StockOperationType.ISSUE:
            raise InvalidReservationConsumptionContextError(
                "Погашение резервов строится только по ISSUE."
            )
        if not isinstance(bindings, tuple) or not isinstance(reservations, tuple):
            raise InvalidReservationConsumptionContextError(
                "Соответствия и снимки резервов передаются в tuple."
            )
        by_reservation: dict[
            StockReservationIdVO, StockReservationExecutionSnapshot
        ] = {}
        pools: dict[AvailabilityPoolIdVO, tuple[AvailabilityPoolKeyVO, UomCodeVO]] = {}
        for reservation in reservations:
            if not isinstance(reservation, StockReservationExecutionSnapshot):
                raise InvalidStockReservationExecutionSnapshotError(
                    "Нужны снимки привязки и версии резервов."
                )
            reservation.ensure_valid()
            if reservation.id in by_reservation:
                raise InvalidReservationConsumptionContextError(
                    "Снимок каждого резерва передаётся один раз."
                )
            identity = (reservation.key, reservation.base_uom)
            if reservation.pool_id in pools and pools[reservation.pool_id] != identity:
                raise InvalidReservationConsumptionContextError(
                    "Один ID пула не может обозначать разные области или единицы."
                )
            pools[reservation.pool_id] = identity
            by_reservation[reservation.id] = reservation
        by_line = {line.id: line for line in execution.lines}
        selected: dict[StockExecutionLineIdVO, StockReservationIdVO] = {}
        for binding in bindings:
            if not isinstance(binding, ReservationExecutionBindingVO):
                raise InvalidReservationExecutionBindingError(
                    "Нужны явные ReservationExecutionBindingVO."
                )
            if binding.execution_line_id in selected:
                raise InvalidReservationConsumptionContextError(
                    "Фактическую строку можно целиком назначить только один раз."
                )
            if (
                binding.execution_line_id not in by_line
                or binding.reservation_id not in by_reservation
            ):
                raise InvalidReservationConsumptionContextError(
                    "Не найдена фактическая строка или снимок назначенного резерва."
                )
            selected[binding.execution_line_id] = binding.reservation_id
        if set(selected.values()) != set(by_reservation):
            raise InvalidReservationConsumptionContextError(
                "Нужны ровно участвующие снимки резервов без лишних."
            )
        quantities: dict[StockReservationIdVO, QuantityVO] = {}
        line_ids: dict[StockReservationIdVO, list[StockExecutionLineIdVO]] = {}
        for line_id in sorted(selected, key=lambda identifier: identifier.uuid.int):
            reservation_id = selected[line_id]
            reservation = by_reservation[reservation_id]
            line = by_line[line_id]
            if (
                reservation.key.inventory_item_id != line.inventory_item_id
                or reservation.key.warehouse_id != execution.warehouse_id
                or reservation.key.owner_id != execution.owner_id
                or reservation.base_uom != line.base_uom
            ):
                raise InvalidReservationConsumptionContextError(
                    "Товар, склад, владелец и базовая единица строки должны соответствовать резерву."
                )
            previous = quantities.get(reservation_id)
            quantities[reservation_id] = (
                line.quantity
                if previous is None
                else QuantityArithmeticPolicy.add(previous, line.quantity)
            )
            line_ids.setdefault(reservation_id, []).append(line_id)
        result = []
        for reservation_id in sorted(
            quantities, key=lambda identifier: identifier.uuid.int
        ):
            reservation = by_reservation[reservation_id]
            consumption = StockReservationConsumptionSnapshot(
                execution_id=execution.id,
                execution_line_ids=tuple(line_ids[reservation_id]),
                reservation_id=reservation.id,
                reservation_version=reservation.version,
                pool_id=reservation.pool_id,
                key=reservation.key,
                base_uom=reservation.base_uom,
                quantity=quantities[reservation_id],
                consumed_at=execution.executed_at,
            )
            consumption.ensure_valid()
            result.append(consumption)
        return tuple(result)
