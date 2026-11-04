from decimal import Decimal

from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionPostingSnapshotError,
)
from src.modules.inventory.domain.stock_execution.posting_snapshot import (
    StockExecutionPostingSnapshot,
)
from src.modules.inventory.domain.stock_execution.value_object.issue_route import (
    IssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.receipt_route import (
    ReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.entity.stock_ledger_entry import (
    StockLedgerEntry,
)
from src.modules.inventory.domain.stock_posting.error import (
    DuplicateStockLedgerEntryError,
    InvalidPostingContextError,
    InvalidStockPostingEntryBindingError,
    OpposingStockPositionMovementsError,
)
from src.modules.inventory.domain.stock_posting.value_object.entry_binding import (
    StockPostingEntryBindingVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO


class StockExecutionPostingPolicy:
    """Сопоставляет физические маршруты позициям и строит точные однонаправленные итоги Ledger."""

    @staticmethod
    def build_entries(
        *,
        execution: StockExecutionPostingSnapshot,
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        entry_bindings: tuple[StockPostingEntryBindingVO, ...],
    ) -> tuple[StockLedgerEntry, ...]:
        """Группирует маршруты по позициям без потери исходной детализации и без встречного сальдирования."""
        if not isinstance(execution, StockExecutionPostingSnapshot):
            raise InvalidStockExecutionPostingSnapshotError(
                "Нужен снимок физических маршрутов исполнения."
            )
        execution.ensure_valid()
        by_dimensions = StockExecutionPostingPolicy._index_positions(positions)
        expected_dimensions = {
            dimensions
            for line in execution.lines
            for dimensions in line.route.dimensions
        }
        if set(by_dimensions) != expected_dimensions:
            raise InvalidPostingContextError(
                "Нужны ровно те позиции, которые соответствуют полным измерениям маршрутов."
            )
        StockExecutionPostingPolicy._ensure_locations(
            execution=execution, locations=locations
        )
        bindings = StockExecutionPostingPolicy._index_bindings(entry_bindings)
        if set(bindings) != {position.id for position in by_dimensions.values()}:
            raise InvalidStockPostingEntryBindingError(
                "Нужно ровно одно соответствие ID записи каждой итоговой позиции."
            )
        grouped: dict[StockPositionIdVO, tuple[bool, QuantityVO]] = {}
        for line in execution.lines:
            if isinstance(line.route, ReceiptExecutionRouteVO):
                movements = ((line.route.destination, True),)
            elif isinstance(line.route, IssueExecutionRouteVO):
                movements = ((line.route.source, False),)
            else:
                movements = ((line.route.source, False), (line.route.destination, True))
            for dimensions, incoming in movements:
                position = by_dimensions[dimensions]
                if position.base_uom != line.base_uom:
                    raise InvalidPostingContextError(
                        "Базовая единица позиции должна совпадать с фактической строкой."
                    )
                previous = grouped.get(position.id)
                if previous is not None and previous[0] is not incoming:
                    raise OpposingStockPositionMovementsError(
                        "Одна позиция участвует в приходе и расходе: нужны отдельные исполнения без скрытого сальдирования."
                    )
                quantity = (
                    line.quantity
                    if previous is None
                    else QuantityArithmeticPolicy.add(previous[1], line.quantity)
                )
                grouped[position.id] = (incoming, quantity)
        by_id = {position.id: position for position in by_dimensions.values()}
        entries = []
        for position_id in sorted(grouped, key=lambda identifier: identifier.uuid.int):
            incoming, quantity = grouped[position_id]
            base_uom = by_id[position_id].base_uom
            entries.append(
                StockLedgerEntry.create(
                    identifier=bindings[position_id],
                    position_id=position_id,
                    quantity_delta=StockDeltaVO(
                        quantity.value if incoming else quantity.value.copy_negate()
                    ),
                    base_uom=base_uom,
                    conversion=QuantityConversionSnapshotVO(
                        quantity=quantity, uom=base_uom, factor_to_base=Decimal(1)
                    ),
                )
            )
        return tuple(entries)

    @staticmethod
    def _index_positions(
        positions: tuple[StockPositionSnapshot, ...],
    ) -> dict[StockDimensionsVO, StockPositionSnapshot]:
        """Требует типизированные позиции с уникальными ID и полными сочетаниями измерений."""
        if not isinstance(positions, tuple):
            raise InvalidPostingContextError("Позиции передаются в tuple снимков.")
        by_dimensions = {}
        ids = set()
        for position in positions:
            if not isinstance(position, StockPositionSnapshot):
                raise InvalidPostingContextError(
                    "Нужны снимки позиций, а не корни агрегатов."
                )
            position.ensure_valid()
            if position.id in ids or position.dimensions in by_dimensions:
                raise InvalidPostingContextError(
                    "ID позиций и сочетания измерений не должны повторяться."
                )
            ids.add(position.id)
            by_dimensions[position.dimensions] = position
        return by_dimensions

    @staticmethod
    def _index_bindings(
        entry_bindings: tuple[StockPostingEntryBindingVO, ...],
    ) -> dict[StockPositionIdVO, StockLedgerEntryIdVO]:
        """Требует явные уникальные ID записей без автоматической генерации внутри Domain."""
        if not isinstance(entry_bindings, tuple):
            raise InvalidStockPostingEntryBindingError(
                "Соответствия позиций и записей передаются в tuple VO."
            )
        by_position = {}
        ids = set()
        for binding in entry_bindings:
            if not isinstance(binding, StockPostingEntryBindingVO):
                raise InvalidStockPostingEntryBindingError(
                    "Нужны StockPostingEntryBindingVO."
                )
            if binding.position_id in by_position or binding.entry_id in ids:
                raise DuplicateStockLedgerEntryError(
                    "Каждая позиция и ID записи должны встречаться один раз."
                )
            ids.add(binding.entry_id)
            by_position[binding.position_id] = binding.entry_id
        return by_position

    @staticmethod
    def _ensure_locations(
        *,
        execution: StockExecutionPostingSnapshot,
        locations: tuple[StockLocationSnapshot, ...],
    ) -> None:
        """Проверяет точный набор адресов и их неизменяемую принадлежность складу исполнения."""
        if not isinstance(locations, tuple):
            raise InvalidPostingContextError("Локации передаются в tuple снимков.")
        ids = set()
        for location in locations:
            if not isinstance(location, StockLocationSnapshot):
                raise InvalidPostingContextError("Нужны снимки участвующих локаций.")
            location.ensure_valid()
            if location.id in ids or location.warehouse_id != execution.warehouse_id:
                raise InvalidPostingContextError(
                    "Локации должны быть уникальны и принадлежать складу исполнения."
                )
            ids.add(location.id)
        expected = {
            dimensions.location_id
            for line in execution.lines
            for dimensions in line.route.dimensions
        }
        if ids != expected:
            raise InvalidPostingContextError(
                "Нужны ровно локации физических маршрутов исполнения."
            )
