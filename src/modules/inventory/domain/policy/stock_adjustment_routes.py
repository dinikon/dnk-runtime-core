from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.stock_execution.value_object.adjustment_route import (
    StockAdjustmentExecutionRouteVO,
)


class StockAdjustmentRoutesPolicy:
    """Проверяет уникальные позиции и единичные направления одного SERIAL в полном факте."""

    @staticmethod
    def ensure_valid(routes: tuple[StockAdjustmentExecutionRouteVO, ...]) -> None:
        """Разрешает пару расход/приход экземпляра, запрещая повтор направления или подмену идентичности."""
        if not isinstance(routes, tuple) or not routes:
            raise StockAdjustmentError("Нужен непустой tuple маршрутов корректировки.")
        positions, dimensions, directions = set(), set(), set()
        identities = {}
        for route in routes:
            if not isinstance(route, StockAdjustmentExecutionRouteVO):
                raise StockAdjustmentError("Нужен маршрут корректировки.")
            detail = route.adjustment
            if route.position_id in positions or detail.dimensions in dimensions:
                raise StockAdjustmentError(
                    "Каждая физическая позиция и комбинация измерений корректируется один раз."
                )
            positions.add(route.position_id)
            dimensions.add(detail.dimensions)
            serial_id = detail.dimensions.serial_id
            if serial_id is not None:
                identity = (
                    detail.dimensions.inventory_item_id,
                    detail.dimensions.lot_id,
                )
                direction = (serial_id, detail.quantity_delta.value.is_signed())
                if direction in directions or (
                    serial_id in identities and identities[serial_id] != identity
                ):
                    raise StockAdjustmentError(
                        "SERIAL допускает одну идентичность и не более одного прихода/расхода."
                    )
                identities[serial_id] = identity
                directions.add(direction)
