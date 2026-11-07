from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.valuation_layer_consumption import (
    ValuationLayerConsumptionPolicy,
)
from src.modules.inventory.domain.policy.valuation_layer_movement import (
    ValuationLayerMovementPolicy,
)
from src.modules.inventory.domain.stock_posting.movement_valuation_snapshot import (
    StockMovementValuationSnapshot,
)
from src.modules.inventory.domain.valuation_layer.basis_snapshot import (
    ValuationLayerBasisSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerMovementConsumptionSnapshotError,
    ValuationLayerTimeError,
)
from src.modules.inventory.domain.valuation_layer.time import normalize_valuation_time
from src.modules.inventory.domain.valuation_layer.value_object.cost_basis import (
    CostBasisVO,
)
from src.modules.inventory.domain.valuation_layer.value_object.identifier import (
    ValuationLayerIdVO,
)
from src.modules.inventory.domain.valuation_layer.value_object.source import (
    ValuationLayerSourceVO,
)
from src.modules.inventory.domain.valuation_layer.value_object.transfer_origin import (
    ValuationLayerTransferOriginVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class ValuationLayerMovementConsumptionSnapshot:
    """Фиксирует изменение одного слоя при потреблении полного количества пары INTERNAL_MOVE."""

    layer: ValuationLayerBasisSnapshot
    movement: StockMovementValuationSnapshot
    remaining_qty_before: QuantityVO
    remaining_qty_after: QuantityVO
    remaining_cost_before: MoneyVO
    remaining_cost_after: MoneyVO
    version_before: int
    version_after: int
    updated_at_before: datetime
    consumed_at: datetime

    @property
    def quantity(self) -> QuantityVO:
        """Возвращает всё перемещённое количество пары в базовой единице."""
        return self.movement.quantity

    @property
    def cost(self) -> MoneyVO:
        """Вычисляет переносимую сумму как разницу проверенных остатков слоя."""
        return self.remaining_cost_before - self.remaining_cost_after

    def destination_basis(
        self, *, identifier: ValuationLayerIdVO, created_at: datetime
    ) -> ValuationLayerBasisSnapshot:
        """Выводит первоначальное основание назначения для создания слоя и проверки журнала."""
        self.ensure_valid()
        at = normalize_valuation_time(created_at)
        if at < self.consumed_at:
            raise ValuationLayerTimeError(
                "Слой назначения нельзя зарегистрировать раньше потребления исходного слоя."
            )
        movement = self.movement
        target = movement.target_position
        basis = ValuationLayerBasisSnapshot(
            id=identifier,
            source=ValuationLayerSourceVO(
                movement.posting_id, movement.pair.incoming_entry_id, target.id
            ),
            inventory_item_id=target.dimensions.inventory_item_id,
            owner_id=target.dimensions.owner_id,
            warehouse_id=movement.warehouse_id,
            base_uom=target.base_uom,
            cost_basis=CostBasisVO(self.quantity, self.cost),
            received_at=self.layer.received_at,
            created_at=at,
            transfer_origin=ValuationLayerTransferOriginVO(
                parent_layer_id=self.layer.id,
                receipt_source=self.layer.source,
                outgoing_entry_id=movement.pair.outgoing_entry_id,
                moved_at=movement.moved_at,
            ),
        )
        basis.ensure_valid()
        return basis

    def ensure_valid(self) -> None:
        """Проверяет основания, переход количества и стоимости, версии и хронологию."""
        ValuationLayerMovementPolicy.ensure_compatible(
            layer=self.layer, movement=self.movement
        )
        expected_before = ValuationLayerConsumptionPolicy.calculate_remaining_cost(
            cost_basis=self.layer.cost_basis, remaining_qty=self.remaining_qty_before
        )
        expected_after = ValuationLayerConsumptionPolicy.calculate_remaining_cost(
            cost_basis=self.layer.cost_basis, remaining_qty=self.remaining_qty_after
        )
        for cost in (self.remaining_cost_before, self.remaining_cost_after):
            if (
                not isinstance(cost, MoneyVO)
                or not isinstance(cost.amount, Decimal)
                or not cost.amount.is_finite()
            ):
                raise InvalidValuationLayerMovementConsumptionSnapshotError(
                    "Нужны конечные денежные остатки до и после переноса."
                )
        if (
            self.remaining_qty_before.value < self.quantity.value
            or QuantityArithmeticPolicy.subtract(
                self.remaining_qty_before, self.quantity
            )
            != self.remaining_qty_after
            or self.remaining_cost_before != expected_before
            or self.remaining_cost_after != expected_after
        ):
            raise InvalidValuationLayerMovementConsumptionSnapshotError(
                "Остатки должны отражать полное количество пары и накопленную стоимость в валюте слоя."
            )
        if (
            type(self.version_before) is not int
            or self.version_before < 0
            or type(self.version_after) is not int
            or self.version_after != self.version_before + 1
        ):
            raise InvalidValuationLayerMovementConsumptionSnapshotError(
                "Нужны последовательные строгие версии слоя."
            )
        normalize_valuation_time(self.updated_at_before)
        normalize_valuation_time(self.consumed_at)
        if (
            self.updated_at_before.utcoffset() != timedelta(0)
            or self.consumed_at.utcoffset() != timedelta(0)
            or self.updated_at_before < self.layer.created_at
            or self.consumed_at < self.updated_at_before
            or self.consumed_at < self.movement.moved_at
        ):
            raise InvalidValuationLayerMovementConsumptionSnapshotError(
                "Регистрация потребления в UTC должна быть не раньше предыдущего изменения и перемещения."
            )
