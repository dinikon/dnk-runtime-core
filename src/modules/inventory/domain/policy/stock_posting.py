from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.entity.stock_ledger_entry import (
    StockLedgerEntry,
)
from src.modules.inventory.domain.stock_posting.error import (
    DuplicateStockLedgerEntryError,
    InvalidPostingContextError,
    InvalidStockPostingValueError,
    StockPostingSignError,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_posting.value_object.posting_source import (
    PostingSourceVO,
)


class StockPostingPolicy:
    """Проверяет состав журнала и соответствие его ссылок неизменяемым атрибутам позиций."""

    @staticmethod
    def normalize_time(posted_at: datetime) -> datetime:
        """Принимает только время с часовым поясом и нормализует его в UTC."""
        if not isinstance(posted_at, datetime) or posted_at.utcoffset() is None:
            raise InvalidStockPostingValueError(
                "Время проведения должно содержать часовой пояс."
            )
        try:
            return posted_at.astimezone(UTC)
        except (OverflowError, ValueError) as exc:
            raise InvalidStockPostingValueError(
                "Время проведения невозможно представить в UTC."
            ) from exc

    @staticmethod
    def ensure_valid(
        *,
        identifier: StockPostingIdVO,
        source: PostingSourceVO,
        operation_type: StockOperationType,
        posted_at: datetime,
        entries: tuple[StockLedgerEntry, ...],
        reversal_of_id: StockPostingIdVO | None,
    ) -> None:
        """Проверяет собственные инварианты проведения без текущих снимков и I/O."""
        if (
            not isinstance(identifier, StockPostingIdVO)
            or not isinstance(source, PostingSourceVO)
            or not isinstance(operation_type, StockOperationType)
            or not isinstance(entries, tuple)
            or not entries
            or (
                reversal_of_id is not None
                and not isinstance(reversal_of_id, StockPostingIdVO)
            )
            or identifier == reversal_of_id
        ):
            raise InvalidStockPostingValueError(
                "Нужны типизированные поля и непустой tuple записей без ссылки на себя."
            )
        StockPostingPolicy.normalize_time(posted_at)
        if posted_at.utcoffset() != timedelta(0):
            raise InvalidStockPostingValueError(
                "Сохранённое время проведения должно быть в UTC."
            )
        entry_ids = set()
        position_ids = set()
        for entry in entries:
            if not isinstance(entry, StockLedgerEntry):
                raise InvalidStockPostingValueError(
                    "Проведение содержит только StockLedgerEntry."
                )
            entry.ensure_valid()
            if entry.id in entry_ids or entry.position_id in position_ids:
                raise DuplicateStockLedgerEntryError(
                    "ID записи и позиция не должны повторяться в проведении."
                )
            entry_ids.add(entry.id)
            position_ids.add(entry.position_id)
            if reversal_of_id is None and (
                (
                    operation_type is StockOperationType.RECEIPT
                    and entry.quantity_delta.value.is_signed()
                )
                or (
                    operation_type is StockOperationType.ISSUE
                    and not entry.quantity_delta.value.is_signed()
                )
            ):
                raise StockPostingSignError(
                    "Знак записи не соответствует виду обычной операции."
                )

    @staticmethod
    def ensure_positions(
        *,
        entries: tuple[StockLedgerEntry, ...],
        positions: tuple[StockPositionSnapshot, ...],
    ) -> None:
        """Требует ровно по одному снимку позиции каждой записи, совпадение единиц и единичные серии."""
        if (
            not isinstance(positions, tuple)
            or not isinstance(entries, tuple)
            or not entries
        ):
            raise InvalidPostingContextError(
                "Нужны непустые записи и tuple снимков позиций."
            )
        by_id = {}
        dimensions = set()
        for position in positions:
            if not isinstance(position, StockPositionSnapshot):
                raise InvalidPostingContextError("Нужны снимки позиций, а не агрегаты.")
            position.ensure_valid()
            if position.id in by_id or position.dimensions in dimensions:
                raise InvalidPostingContextError(
                    "Снимки позиций и их измерения не должны повторяться."
                )
            by_id[position.id] = position
            dimensions.add(position.dimensions)
        expected_ids = set()
        entry_ids = set()
        serial_directions = set()
        for entry in entries:
            if not isinstance(entry, StockLedgerEntry):
                raise InvalidPostingContextError("Нужны типизированные записи журнала.")
            entry.ensure_valid()
            if entry.position_id in expected_ids or entry.id in entry_ids:
                raise DuplicateStockLedgerEntryError(
                    "Записи и позиции не должны повторяться."
                )
            expected_ids.add(entry.position_id)
            entry_ids.add(entry.id)
            position = by_id.get(entry.position_id)
            if position is None or entry.base_uom != position.base_uom:
                raise InvalidPostingContextError(
                    "Снимок позиции должен существовать и иметь ту же базовую единицу."
                )
            if (
                position.dimensions.serial_id is not None
                and entry.quantity_delta.value.copy_abs() != Decimal(1)
            ):
                raise InvalidPostingContextError(
                    "Движение конкретного серийного экземпляра равно одной штуке."
                )
            if position.dimensions.serial_id is not None:
                direction = (
                    position.dimensions.serial_id,
                    entry.quantity_delta.value.is_signed(),
                )
                if direction in serial_directions:
                    raise InvalidPostingContextError(
                        "Один экземпляр не может иметь несколько приходов или расходов в одном проведении."
                    )
                serial_directions.add(direction)
        if expected_ids != set(by_id):
            raise InvalidPostingContextError("Лишние снимки позиций не допускаются.")
