from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.valuation_layer_consumption import (
    ValuationLayerConsumptionPolicy,
)
from src.modules.inventory.domain.policy.valuation_layer_issue import (
    ValuationLayerIssuePolicy,
)
from src.modules.inventory.domain.policy.valuation_layer_movement import (
    ValuationLayerMovementPolicy,
)
from src.modules.inventory.domain.stock_posting.issue_valuation_snapshot import (
    StockIssueValuationSnapshot,
)
from src.modules.inventory.domain.stock_posting.fifo_plan_snapshot import (
    StockIssueFifoPlanSnapshot,
)
from src.modules.inventory.domain.stock_posting.movement_valuation_snapshot import (
    StockMovementValuationSnapshot,
)
from src.modules.inventory.domain.valuation_layer.basis_snapshot import (
    ValuationLayerBasisSnapshot,
)
from src.modules.inventory.domain.valuation_layer.fifo_snapshot import (
    ValuationLayerFifoSnapshot,
)
from src.modules.inventory.domain.valuation_layer.consumption_snapshot import (
    ValuationLayerConsumptionSnapshot,
)
from src.modules.inventory.domain.stock_posting.receipt_valuation_snapshot import (
    StockReceiptValuationSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerReceiptSnapshotError,
    InvalidValuationLayerValueError,
    ValuationLayerConsumptionError,
    ValuationLayerTimeError,
    ValuationLayerVersionConflictError,
    InvalidStockIssueFifoPlanError,
    ValuationFifoStateConflictError,
)
from src.modules.inventory.domain.valuation_layer.movement_consumption_snapshot import (
    ValuationLayerMovementConsumptionSnapshot,
)
from src.modules.inventory.domain.valuation_layer.time import normalize_valuation_time
from src.modules.inventory.domain.valuation_layer.receipt_snapshot import (
    ValuationLayerReceiptSnapshot,
)
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
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class ValuationLayer:
    """Хранит первоначальную и остаточную стоимость запаса на конкретной позиции."""

    id: ValuationLayerIdVO
    source: ValuationLayerSourceVO
    inventory_item_id: InventoryItemIdVO
    owner_id: StockOwnerIdVO
    warehouse_id: WarehouseIdVO
    base_uom: UomCodeVO
    cost_basis: CostBasisVO
    received_at: datetime
    created_at: datetime
    remaining_qty: QuantityVO
    remaining_cost: MoneyVO
    updated_at: datetime
    version: int
    transfer_origin: ValuationLayerTransferOriginVO | None = None

    @classmethod
    def create_from_receipt(
        cls,
        *,
        identifier: ValuationLayerIdVO,
        receipt: StockReceiptValuationSnapshot,
        total_cost: MoneyVO,
        created_at: datetime,
    ) -> Self:
        """Выводит идентичность и количество из проверенного прихода, фиксируя явно переданную полную стоимость."""
        if not isinstance(receipt, StockReceiptValuationSnapshot):
            raise InvalidValuationLayerValueError(
                "Нужно специализированное основание StockReceiptValuationSnapshot."
            )
        receipt.ensure_valid()
        return cls.restore(
            identifier=identifier,
            source=ValuationLayerSourceVO(
                receipt.posting_id, receipt.ledger_entry_id, receipt.position_id
            ),
            inventory_item_id=receipt.inventory_item_id,
            owner_id=receipt.owner_id,
            warehouse_id=receipt.warehouse_id,
            base_uom=receipt.base_uom,
            cost_basis=CostBasisVO(receipt.quantity, total_cost),
            received_at=receipt.received_at,
            created_at=created_at,
            remaining_qty=receipt.quantity,
            remaining_cost=total_cost,
            updated_at=created_at,
            version=0,
        )

    @classmethod
    def create_from_movement(
        cls,
        *,
        identifier: ValuationLayerIdVO,
        consumption: ValuationLayerMovementConsumptionSnapshot,
        created_at: datetime,
    ) -> Self:
        """Создаёт слой на позиции назначения с перенесённой стоимостью и прежней FIFO-датой."""
        if not isinstance(consumption, ValuationLayerMovementConsumptionSnapshot):
            raise InvalidValuationLayerValueError(
                "Нужен специализированный результат потребления по INTERNAL_MOVE."
            )
        basis = consumption.destination_basis(
            identifier=identifier, created_at=created_at
        )
        return cls.restore(
            identifier=basis.id,
            source=basis.source,
            inventory_item_id=basis.inventory_item_id,
            owner_id=basis.owner_id,
            warehouse_id=basis.warehouse_id,
            base_uom=basis.base_uom,
            cost_basis=basis.cost_basis,
            received_at=basis.received_at,
            created_at=basis.created_at,
            remaining_qty=basis.cost_basis.quantity,
            remaining_cost=basis.cost_basis.total_cost,
            updated_at=basis.created_at,
            version=0,
            transfer_origin=basis.transfer_origin,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: ValuationLayerIdVO,
        source: ValuationLayerSourceVO,
        inventory_item_id: InventoryItemIdVO,
        owner_id: StockOwnerIdVO,
        warehouse_id: WarehouseIdVO,
        base_uom: UomCodeVO,
        cost_basis: CostBasisVO,
        received_at: datetime,
        created_at: datetime,
        remaining_qty: QuantityVO,
        remaining_cost: MoneyVO,
        updated_at: datetime,
        version: int,
        transfer_origin: ValuationLayerTransferOriginVO | None = None,
    ) -> Self:
        """Восстанавливает все собственные исторические поля без чтения проведения, цен и текущих справочников."""
        layer = cls(
            identifier,
            source,
            inventory_item_id,
            owner_id,
            warehouse_id,
            base_uom,
            cost_basis,
            normalize_valuation_time(received_at),
            normalize_valuation_time(created_at),
            remaining_qty,
            remaining_cost,
            normalize_valuation_time(updated_at),
            version,
            transfer_origin,
        )
        layer._validate()
        return layer

    def receipt_valuation_snapshot(self) -> ValuationLayerReceiptSnapshot:
        """Экспортирует первоначальное основание слоя закупочного прихода для журнала RECEIPT."""
        basis = self.basis_snapshot()
        if not isinstance(basis, ValuationLayerReceiptSnapshot):
            raise InvalidValuationLayerReceiptSnapshotError(
                "Для приходной оценки нужен слой закупочного прихода."
            )
        return basis

    def basis_snapshot(self) -> ValuationLayerBasisSnapshot:
        """Экспортирует проверенную исходную оценку слоя независимо от его остатка."""
        self._validate()
        return self._basis_snapshot()

    def _basis_snapshot(self) -> ValuationLayerBasisSnapshot:
        """Собирает основание подходящего вида из собственных исторических полей слоя."""
        fields = (
            self.id,
            self.source,
            self.inventory_item_id,
            self.owner_id,
            self.warehouse_id,
            self.base_uom,
            self.cost_basis,
            self.received_at,
            self.created_at,
        )
        if self.transfer_origin is None:
            return ValuationLayerReceiptSnapshot(*fields)
        return ValuationLayerBasisSnapshot(*fields, self.transfer_origin)

    def fifo_snapshot(self) -> ValuationLayerFifoSnapshot:
        """Возвращает проверенное состояние кандидата FIFO с первоначальным основанием и текущей версией."""
        snapshot = ValuationLayerFifoSnapshot(
            self.basis_snapshot(),
            self.remaining_qty,
            self.remaining_cost,
            self.version,
            self.updated_at,
        )
        snapshot.ensure_valid()
        return snapshot

    def consume_fifo_allocation(
        self, plan: StockIssueFifoPlanSnapshot, *, updated_at: datetime
    ) -> tuple[Self, ValuationLayerConsumptionSnapshot]:
        """Применяет собственное назначение только по неизменившемуся состоянию кандидата FIFO."""
        self._validate()
        if not isinstance(plan, StockIssueFifoPlanSnapshot):
            raise InvalidStockIssueFifoPlanError(
                "Нужен проверяемый план FIFO одной записи ISSUE."
            )
        plan.ensure_valid()
        allocation = next(
            (value for value in plan.allocations if value.layer_id == self.id), None
        )
        if allocation is None:
            raise ValuationFifoStateConflictError("Слой не выбран в этом плане FIFO.")
        if self.version != allocation.expected_version:
            raise ValuationLayerVersionConflictError(
                "Версия выбранного FIFO-слоя устарела."
            )
        candidate = next(
            value for value in plan.candidates if value.layer.id == self.id
        )
        if self.fifo_snapshot() != candidate:
            raise ValuationFifoStateConflictError(
                "Состояние слоя отличается от сохранённого кандидата FIFO."
            )
        return self.consume_from_issue(
            plan.issue,
            quantity=allocation.quantity,
            expected_version=allocation.expected_version,
            updated_at=updated_at,
        )

    def is_exhausted(self) -> bool:
        """Определяет исчерпание по количеству: нулевая стоимость допускает ненулевой запас."""
        self._validate()
        return self.remaining_qty.value == 0

    def consume(
        self,
        quantity: QuantityVO,
        *,
        expected_version: int,
        updated_at: datetime,
    ) -> Self:
        """Потребляет положительное базовое количество и возвращает новый слой с накопленной оценкой."""
        self._validate()
        if type(expected_version) is not int or expected_version < 0:
            raise InvalidValuationLayerValueError(
                "Ожидаемая версия должна быть целым числом от нуля."
            )
        if expected_version != self.version:
            raise ValuationLayerVersionConflictError(
                "Версия стоимостного слоя устарела."
            )
        at = normalize_valuation_time(updated_at)
        if at < self.updated_at:
            raise ValuationLayerTimeError(
                "Потребление не может предшествовать последнему изменению слоя."
            )
        if (
            not isinstance(quantity, QuantityVO)
            or not isinstance(quantity.value, Decimal)
            or not quantity.value.is_finite()
            or quantity.value <= 0
            or quantity.value > self.remaining_qty.value
        ):
            raise ValuationLayerConsumptionError(
                "Нужно положительное количество не больше остатка стоимостного слоя."
            )
        remaining_qty = QuantityArithmeticPolicy.subtract(self.remaining_qty, quantity)
        layer = replace(
            self,
            remaining_qty=remaining_qty,
            remaining_cost=ValuationLayerConsumptionPolicy.calculate_remaining_cost(
                cost_basis=self.cost_basis, remaining_qty=remaining_qty
            ),
            updated_at=at,
            version=self.version + 1,
        )
        layer._validate()
        return layer

    def consume_from_issue(
        self,
        issue: StockIssueValuationSnapshot,
        *,
        quantity: QuantityVO | None = None,
        expected_version: int,
        updated_at: datetime,
    ) -> tuple[Self, ValuationLayerConsumptionSnapshot]:
        """Потребляет выбранную часть ISSUE или всё количество по умолчанию, возвращая новый слой и проверенный переход."""
        basis = self.basis_snapshot()
        ValuationLayerIssuePolicy.ensure_compatible(layer=basis, issue=issue)
        selected = issue.quantity if quantity is None else quantity
        ValuationLayerIssuePolicy.ensure_quantity(issue=issue, quantity=selected)
        at = normalize_valuation_time(updated_at)
        if at < issue.issued_at:
            raise ValuationLayerTimeError(
                "Регистрация потребления не может предшествовать физическому расходу."
            )
        layer = self.consume(selected, expected_version=expected_version, updated_at=at)
        consumption = ValuationLayerConsumptionSnapshot(
            layer=basis,
            issue=issue,
            quantity=selected,
            cost=self.remaining_cost - layer.remaining_cost,
            remaining_qty_before=self.remaining_qty,
            remaining_qty_after=layer.remaining_qty,
            remaining_cost_before=self.remaining_cost,
            remaining_cost_after=layer.remaining_cost,
            version_before=self.version,
            version_after=layer.version,
            updated_at_before=self.updated_at,
            consumed_at=layer.updated_at,
        )
        consumption.ensure_valid()
        return layer, consumption

    def consume_for_movement(
        self,
        movement: StockMovementValuationSnapshot,
        *,
        expected_version: int,
        updated_at: datetime,
    ) -> tuple[Self, ValuationLayerMovementConsumptionSnapshot]:
        """Потребляет всё количество пары INTERNAL_MOVE и возвращает проверенный переход стоимости."""
        basis = self.basis_snapshot()
        ValuationLayerMovementPolicy.ensure_compatible(layer=basis, movement=movement)
        at = normalize_valuation_time(updated_at)
        if at < movement.moved_at:
            raise ValuationLayerTimeError(
                "Регистрация потребления не может предшествовать физическому перемещению."
            )
        layer = self.consume(
            movement.quantity, expected_version=expected_version, updated_at=at
        )
        consumption = ValuationLayerMovementConsumptionSnapshot(
            layer=basis,
            movement=movement,
            remaining_qty_before=self.remaining_qty,
            remaining_qty_after=layer.remaining_qty,
            remaining_cost_before=self.remaining_cost,
            remaining_cost_after=layer.remaining_cost,
            version_before=self.version,
            version_after=layer.version,
            updated_at_before=self.updated_at,
            consumed_at=layer.updated_at,
        )
        consumption.ensure_valid()
        return layer, consumption

    def _validate(self) -> None:
        """Проверяет собственные ссылки, стоимость, единицу и UTC-хронологию неизменяемого слоя."""
        self._basis_snapshot().ensure_valid()
        if type(self.version) is not int or self.version < 0:
            raise InvalidValuationLayerValueError(
                "Версия слоя должна быть целым числом от нуля."
            )
        expected_cost = ValuationLayerConsumptionPolicy.calculate_remaining_cost(
            cost_basis=self.cost_basis, remaining_qty=self.remaining_qty
        )
        if (
            not isinstance(self.remaining_cost, MoneyVO)
            or not isinstance(self.remaining_cost.amount, Decimal)
            or not self.remaining_cost.amount.is_finite()
            or self.remaining_cost != expected_cost
        ):
            raise InvalidValuationLayerValueError(
                "Остаточная стоимость должна соответствовать валюте и накопленной оценке количества слоя."
            )
        normalize_valuation_time(self.updated_at)
        if (
            self.updated_at.utcoffset() != timedelta(0)
            or self.updated_at < self.created_at
        ):
            raise ValuationLayerTimeError(
                "Изменение слоя должно храниться в UTC и следовать за регистрацией."
            )
