"""Проверяет идентичность возврата и независимый лимит исходного факта без БД."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4
import unittest
from test.test_inventory_execution_posting_domain import (
    ExecutionPostingDomainTests as Support,
)
from src.modules.inventory.domain.stock_execution.return_origin_snapshot import (
    StockReturnOriginSnapshot,
    StockReturnOriginLineSnapshot,
    StockReturnUsageSnapshot,
    StockReturnFactSnapshot,
)
from src.modules.inventory.domain.policy.stock_return import StockReturnPolicy
from src.modules.inventory.domain.stock_document.return_error import (
    InvalidStockReturnError,
    StockReturnLimitError,
)
from src.modules.inventory.domain.stock_document.value_object.return_details import (
    StockReturnDetailsVO,
)
from src.modules.inventory.domain.stock_document.value_object.return_direction import (
    ReturnDirection,
)
from src.modules.inventory.domain.stock_document.value_object.return_reason import (
    ReturnReasonVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.return_receipt_route import (
    ReturnReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.return_issue_route import (
    ReturnIssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.value_object.stock_status import StockStatus


class StockReturnDomainTests(unittest.TestCase):
    """Фактические возвраты обязаны хранить исходную идентичность и точные количества."""

    def setUp(self) -> None:
        """Готовит два исходных факта одного SKU с независимыми пределами."""
        self.f = Support()
        self.f.setUp()
        self.origin = StockReturnOriginSnapshot(
            StockExecutionIdVO(uuid4()),
            StockOperationType.ISSUE,
            self.f.warehouse.id,
            self.f.owner,
            self.f.time,
            StockPostingIdVO(uuid4()),
            False,
            None,
            tuple(
                StockReturnOriginLineSnapshot(
                    StockExecutionLineIdVO(uuid4()),
                    self.f.a.dimensions,
                    QuantityVO(Decimal(q)),
                    self.f.item.base_uom,
                )
                for q in ("3.15", "7.05")
            ),
        )
        self.details = StockReturnDetailsVO(
            self.origin.id, ReturnDirection.FROM_RECIPIENT, ReturnReasonVO("Возврат")
        )
        self.usage = tuple(
            StockReturnUsageSnapshot(v.id, QuantityVO(Decimal(0)))
            for v in self.origin.lines
        )

    def fact(self, quantity: str = "1.05") -> StockReturnFactSnapshot:
        """Меняет только разрешённые адрес и состояние принимаемого товара."""
        return StockReturnFactSnapshot(
            self.origin.lines[0].id,
            replace(
                self.f.a.dimensions,
                location_id=self.f.locations[1].id,
                stock_status=StockStatus.QUARANTINE,
            ),
            QuantityVO(Decimal(quantity)),
            self.f.item.base_uom,
        )

    def validate(
        self, facts: tuple[StockReturnFactSnapshot, ...], **changes: object
    ) -> None:
        """Проверяет факт чистой бизнес-политикой без загрузки агрегатов."""
        StockReturnPolicy.ensure_facts(
            **(
                dict(
                    details=self.details,
                    warehouse_id=self.f.warehouse.id,
                    owner_id=self.f.owner,
                    facts=facts,
                    origin=self.origin,
                    usage=self.usage,
                )
                | changes
            )
        )

    def test_direction_derived_and_other_operations_rejected(self) -> None:
        """Разрешены только противоположные стороны обычного прихода и расхода."""
        for kind in StockOperationType:
            origin = replace(self.origin, operation_type=kind)
            if kind in (StockOperationType.RECEIPT, StockOperationType.ISSUE):
                self.assertEqual(
                    StockReturnPolicy.direction(origin),
                    (
                        ReturnDirection.TO_SUPPLIER
                        if kind is StockOperationType.RECEIPT
                        else ReturnDirection.FROM_RECIPIENT
                    ),
                )
            else:
                with self.assertRaises(InvalidStockReturnError):
                    StockReturnPolicy.direction(origin)
        for change in ({"posting_id": None}, {"is_compensated": True}, {"lines": ()}):
            with self.assertRaises(InvalidStockReturnError):
                StockReturnPolicy.direction(replace(self.origin, **change))

    def test_splits_share_exact_limit_without_float_rounding(self) -> None:
        """Два распределения суммируются; отдельная фактическая строка не покрывает превышение."""
        self.validate((self.fact("1.05"), self.fact("2.10")))
        with self.assertRaises(StockReturnLimitError) as error:
            self.validate((self.fact("1.05"), self.fact("2.15")))
        self.assertEqual(error.exception.remaining.value, Decimal("3.15"))
        self.assertEqual(error.exception.requested.value, Decimal("3.20"))
        used = (
            replace(self.usage[0], returned_quantity=QuantityVO(Decimal("2.10"))),
            self.usage[1],
        )
        self.validate((self.fact(),), usage=used)
        with self.assertRaises(StockReturnLimitError):
            self.validate((self.fact("1.10"),), usage=used)

    def test_identity_cannot_be_replaced(self) -> None:
        """Адрес и состояние могут отличаться; товар, владелец, LOT/SERIAL обязаны совпасть."""
        self.validate((self.fact(),))
        from src.modules.inventory.domain.stock_lot.value_object.identifier import (
            StockLotIdVO,
        )
        from src.modules.inventory.domain.stock_serial.value_object.identifier import (
            StockSerialIdVO,
        )

        for changes in (
            {"inventory_item_id": type(self.f.item.id)(uuid4())},
            {"owner_id": type(self.f.owner)(uuid4())},
            {"lot_id": StockLotIdVO(uuid4())},
            {"serial_id": StockSerialIdVO(uuid4())},
        ):
            with self.assertRaises(InvalidStockReturnError):
                self.validate(
                    (
                        replace(
                            self.fact(),
                            dimensions=replace(self.fact().dimensions, **changes),
                        ),
                    )
                )
        with self.assertRaises(InvalidStockReturnError):
            self.validate(
                (replace(self.fact(), origin_line_id=StockExecutionLineIdVO(uuid4())),)
            )
        with self.assertRaises(InvalidStockReturnError):
            self.validate(
                (self.fact(),),
                details=replace(self.details, direction=ReturnDirection.TO_SUPPLIER),
            )

    def test_full_usage_required_even_for_unselected_line(self) -> None:
        """Частичный, повторный либо чужой снимок возвратов не позволяет обойти проверку."""
        for usage in (
            (),
            self.usage[:1],
            (self.usage[0], self.usage[0]),
            (
                self.usage[0],
                replace(self.usage[1], origin_line_id=StockExecutionLineIdVO(uuid4())),
            ),
        ):
            with self.assertRaises(InvalidStockReturnError):
                self.validate((self.fact(),), usage=usage)
        with self.assertRaises(InvalidStockReturnError):
            self.validate(())
        with self.assertRaises(InvalidStockReturnError):
            self.validate((self.fact("0"),))

    def test_posting_revalidates_origin_even_for_restored_execution(self) -> None:
        """Создание Ledger не доверяет восстановленному исполнению без актуального лимита."""
        for direction, route, origin, sign in (
            (
                ReturnDirection.FROM_RECIPIENT,
                ReturnReceiptExecutionRouteVO,
                self.origin,
                1,
            ),
            (
                ReturnDirection.TO_SUPPLIER,
                ReturnIssueExecutionRouteVO,
                replace(self.origin, operation_type=StockOperationType.RECEIPT),
                -1,
            ),
        ):
            execution = self.f.execution(
                (
                    self.f.line(
                        quantity="2.10",
                        route=route(self.origin.lines[0].id, self.f.a.dimensions),
                    ),
                ),
                kind=StockOperationType.RETURN,
                return_details=replace(self.details, direction=direction),
            )
            with self.assertRaises(InvalidStockReturnError):
                self.f.posting(execution)
            posting = self.f.posting(
                execution, return_origin=origin, return_usage=self.usage
            )
            self.assertEqual(
                posting.entries[0].quantity_delta.value, Decimal("2.10") * sign
            )
            with self.assertRaises(StockReturnLimitError):
                self.f.posting(
                    execution,
                    return_origin=origin,
                    return_usage=(
                        replace(
                            self.usage[0], returned_quantity=QuantityVO(Decimal("2.10"))
                        ),
                        self.usage[1],
                    ),
                )
            with self.assertRaises(InvalidStockReturnError):
                self.f.posting(
                    execution,
                    return_origin=replace(
                        origin, executed_at=origin.executed_at + timedelta(days=1)
                    ),
                    return_usage=self.usage,
                )
