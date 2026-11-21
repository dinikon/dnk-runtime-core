from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.policy.stock_adjustment_routes import (
    StockAdjustmentRoutesPolicy,
)
from src.modules.inventory.domain.stock_execution.value_object.adjustment_route import (
    StockAdjustmentExecutionRouteVO,
)
from src.modules.inventory.domain.stock_serial.presence_snapshot import (
    StockSerialPresenceSnapshot,
)


class StockSerialPresencePolicy:
    """Проверяет до/после всего серийного изменения по явно полному текущему присутствию."""

    @staticmethod
    def ensure_compatible(
        *,
        routes: tuple[StockAdjustmentExecutionRouteVO, ...],
        presence: tuple[StockSerialPresenceSnapshot, ...],
    ) -> None:
        """Запрещает создание второго положительного присутствия и неподтверждённый расход экземпляра."""
        StockAdjustmentRoutesPolicy.ensure_valid(routes)
        if not isinstance(presence, tuple):
            raise StockAdjustmentError(
                "Нужен tuple текущего присутствия затронутых SERIAL."
            )
        by_serial = {}
        for snapshot in presence:
            if not isinstance(snapshot, StockSerialPresenceSnapshot):
                raise StockAdjustmentError("Нужен снимок присутствия SERIAL.")
            snapshot.ensure_valid()
            if snapshot.serial_id in by_serial:
                raise StockAdjustmentError("Снимок присутствия SERIAL повторяется.")
            by_serial[snapshot.serial_id] = snapshot
        serial_ids = {
            route.adjustment.dimensions.serial_id
            for route in routes
            if route.adjustment.dimensions.serial_id is not None
        }
        if set(by_serial) != serial_ids:
            raise StockAdjustmentError(
                "Нужно явное присутствие или отсутствие каждого затронутого SERIAL без лишних снимков."
            )
        for serial_id, snapshot in by_serial.items():
            before = {position.id: position for position in snapshot.positions}
            after = set(before)
            for route in routes:
                detail = route.adjustment
                if detail.dimensions.serial_id != serial_id:
                    continue
                for position in snapshot.positions:
                    if (
                        position.dimensions.inventory_item_id,
                        position.dimensions.lot_id,
                    ) != (
                        detail.dimensions.inventory_item_id,
                        detail.dimensions.lot_id,
                    ):
                        raise StockAdjustmentError(
                            "Существующий SERIAL имеет другую идентичность."
                        )
                current = before.get(route.position_id)
                if detail.expected_qty.value == 1:
                    if (
                        current is None
                        or current.dimensions != detail.dimensions
                        or current.version != route.expected_position_version
                    ):
                        raise StockAdjustmentError(
                            "Расход SERIAL не совпадает с его текущим присутствием и версией."
                        )
                elif current is not None:
                    raise StockAdjustmentError(
                        "Исходный ноль SERIAL противоречит его положительному присутствию."
                    )
                if detail.target_qty.value == 1:
                    after.add(route.position_id)
                else:
                    after.discard(route.position_id)
            if len(after) > 1:
                raise StockAdjustmentError(
                    "Корректировка создаёт второе положительное присутствие SERIAL."
                )
