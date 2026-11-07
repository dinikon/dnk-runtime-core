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
from src.modules.inventory.domain.stock_posting.issue_valuation_snapshot import (
    StockIssueValuationSnapshot,
)
from src.modules.inventory.domain.valuation_layer.consumption_snapshot import (
    ValuationLayerConsumptionSnapshot,
)
from src.modules.inventory.domain.stock_posting.receipt_valuation_snapshot import (
    StockReceiptValuationSnapshot,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerValueError,
    ValuationLayerConsumptionError,
    ValuationLayerTimeError,
    ValuationLayerVersionConflictError,
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
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class ValuationLayer:
    """Хранит первоначальную и остаточную стоимость поступления без изменения физического запаса."""

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
        )
        layer._validate()
        return layer

    def receipt_valuation_snapshot(self) -> ValuationLayerReceiptSnapshot:
        """Возвращает проверенную первоначальную стоимость независимо от последующего потребления слоя."""
        self._validate()
        snapshot = ValuationLayerReceiptSnapshot(
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
        snapshot.ensure_valid()
        return snapshot

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
        expected_version: int,
        updated_at: datetime,
    ) -> tuple[Self, ValuationLayerConsumptionSnapshot]:
        """Потребляет полную запись ISSUE одним слоем и возвращает новый корень с проверенным результатом перехода."""
        basis = self.receipt_valuation_snapshot()
        ValuationLayerIssuePolicy.ensure_compatible(layer=basis, issue=issue)
        at = normalize_valuation_time(updated_at)
        if at < issue.issued_at:
            raise ValuationLayerTimeError(
                "Регистрация потребления не может предшествовать физическому расходу."
            )
        layer = self.consume(
            issue.quantity, expected_version=expected_version, updated_at=at
        )
        consumption = ValuationLayerConsumptionSnapshot(
            layer=basis,
            issue=issue,
            quantity=issue.quantity,
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

    def _validate(self) -> None:
        """Проверяет собственные ссылки, стоимость, единицу и UTC-хронологию неизменяемого слоя."""
        if (
            not isinstance(self.id, ValuationLayerIdVO)
            or not isinstance(self.source, ValuationLayerSourceVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.cost_basis, CostBasisVO)
        ):
            raise InvalidValuationLayerValueError(
                "Нужны номинальные поля стоимостного слоя и CostBasisVO."
            )
        self.source.ensure_valid()
        self.cost_basis.ensure_valid()
        get_uom(self.base_uom)
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
        normalize_valuation_time(self.received_at)
        normalize_valuation_time(self.created_at)
        normalize_valuation_time(self.updated_at)
        if (
            self.received_at.utcoffset() != timedelta(0)
            or self.created_at.utcoffset() != timedelta(0)
            or self.updated_at.utcoffset() != timedelta(0)
            or self.created_at < self.received_at
            or self.updated_at < self.created_at
        ):
            raise ValuationLayerTimeError(
                "Даты слоя хранятся в UTC: поступление <= регистрация <= изменение."
            )
