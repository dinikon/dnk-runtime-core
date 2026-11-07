from src.modules.inventory.domain.stock_posting.movement_valuation_snapshot import (
    StockMovementValuationSnapshot,
)
from src.modules.inventory.domain.valuation_layer.basis_snapshot import (
    ValuationLayerBasisSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import (
    ValuationLayerMovementMismatchError,
    ValuationLayerTimeError,
)


class ValuationLayerMovementPolicy:
    """Проверяет применимость пары INTERNAL_MOVE к слою закупочного прихода."""

    @staticmethod
    def ensure_compatible(
        *,
        layer: ValuationLayerBasisSnapshot,
        movement: StockMovementValuationSnapshot,
    ) -> None:
        """Сверяет источник, учётные измерения, целостность серийного слоя и момент перемещения."""
        if not isinstance(layer, ValuationLayerBasisSnapshot) or not isinstance(
            movement, StockMovementValuationSnapshot
        ):
            raise ValuationLayerMovementMismatchError(
                "Нужны специализированные снимки слоя и пары INTERNAL_MOVE."
            )
        layer.ensure_valid()
        movement.ensure_valid()
        if layer.transfer_origin is not None:
            raise ValuationLayerMovementMismatchError(
                "Этот перенос поддерживает слой первоначального прихода."
            )
        position = movement.source_position
        if layer.source.posting_id == movement.posting_id or (
            layer.source.position_id,
            layer.inventory_item_id,
            layer.owner_id,
            layer.warehouse_id,
            layer.base_uom,
        ) != (
            position.id,
            position.dimensions.inventory_item_id,
            position.dimensions.owner_id,
            movement.warehouse_id,
            position.base_uom,
        ):
            raise ValuationLayerMovementMismatchError(
                "Перенос требует отдельного проведения и слоя исходной позиции с теми же учётными измерениями."
            )
        if (
            position.dimensions.serial_id is not None
            and layer.cost_basis.quantity.value != 1
        ):
            raise ValuationLayerMovementMismatchError(
                "Слой серийного экземпляра должен содержать исходную одну PCS."
            )
        if movement.moved_at < layer.available_at:
            raise ValuationLayerTimeError(
                "Физическое перемещение не может предшествовать доступности исходного слоя."
            )
