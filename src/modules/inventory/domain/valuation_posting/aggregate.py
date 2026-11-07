from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Self

from src.modules.inventory.domain.policy.stock_receipt_valuation_posting import (
    StockReceiptValuationPostingPolicy,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.valuation_layer.receipt_snapshot import (
    ValuationLayerReceiptSnapshot,
)
from src.modules.inventory.domain.valuation_posting.entity.valuation_entry import (
    ValuationEntry,
)
from src.modules.inventory.domain.valuation_posting.error import (
    DuplicateValuationEntryError,
    InvalidValuationPostingValueError,
    ValuationPostingTimeError,
)
from src.modules.inventory.domain.valuation_posting.time import (
    normalize_valuation_posting_time,
)
from src.modules.inventory.domain.valuation_posting.value_object.entry_binding import (
    ValuationEntryBindingVO,
)
from src.modules.inventory.domain.valuation_posting.value_object.identifier import (
    ValuationPostingIdVO,
)


@dataclass(frozen=True, slots=True)
class ValuationPosting:
    """Фиксирует неизменяемую первоначальную стоимость полного физического прихода."""

    id: ValuationPostingIdVO
    stock_posting_id: StockPostingIdVO
    operation_type: StockOperationType
    stock_posted_at: datetime
    posted_at: datetime
    entries: tuple[ValuationEntry, ...]

    @classmethod
    def create_from_receipt(
        cls,
        *,
        identifier: ValuationPostingIdVO,
        posting: StockPostingSnapshot,
        layers: tuple[ValuationLayerReceiptSnapshot, ...],
        entry_bindings: tuple[ValuationEntryBindingVO, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        posted_at: datetime,
    ) -> Self:
        """Выводит записи из проверенных первоначальных слоёв, не изменяя их и физическое проведение."""
        entries = StockReceiptValuationPostingPolicy.build_entries(
            posting=posting,
            layers=layers,
            entry_bindings=entry_bindings,
            positions=positions,
            locations=locations,
            posted_at=posted_at,
        )
        return cls.restore(
            identifier=identifier,
            stock_posting_id=posting.id,
            operation_type=posting.operation_type,
            stock_posted_at=posting.posted_at,
            posted_at=posted_at,
            entries=entries,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: ValuationPostingIdVO,
        stock_posting_id: StockPostingIdVO,
        operation_type: StockOperationType,
        stock_posted_at: datetime,
        posted_at: datetime,
        entries: tuple[ValuationEntry, ...],
    ) -> Self:
        """Восстанавливает весь собственный исторический состав без повторной загрузки внешних оснований."""
        posting = cls(
            identifier,
            stock_posting_id,
            operation_type,
            normalize_valuation_posting_time(stock_posted_at),
            normalize_valuation_posting_time(posted_at),
            entries,
        )
        posting._validate()
        return posting

    def _validate(self) -> None:
        """Проверяет собственные типы, непустой состав, уникальность ссылок и UTC-хронологию факта."""
        if (
            not isinstance(self.id, ValuationPostingIdVO)
            or not isinstance(self.stock_posting_id, StockPostingIdVO)
            or self.operation_type is not StockOperationType.RECEIPT
            or not isinstance(self.entries, tuple)
            or not self.entries
        ):
            raise InvalidValuationPostingValueError(
                "Нужны номинальные ID, операция RECEIPT и непустой tuple записей стоимости."
            )
        normalize_valuation_posting_time(self.stock_posted_at)
        normalize_valuation_posting_time(self.posted_at)
        if (
            self.stock_posted_at.utcoffset() != timedelta(0)
            or self.posted_at.utcoffset() != timedelta(0)
            or self.posted_at < self.stock_posted_at
        ):
            raise ValuationPostingTimeError(
                "Даты хранятся в UTC; регистрация стоимости не раньше физического прихода."
            )
        entry_ids = set()
        ledger_ids = set()
        layer_ids = set()
        position_ids = set()
        for entry in self.entries:
            if not isinstance(entry, ValuationEntry):
                raise InvalidValuationPostingValueError(
                    "Проведение содержит только дочерние ValuationEntry."
                )
            entry.ensure_valid()
            if (
                entry.id in entry_ids
                or entry.ledger_entry_id in ledger_ids
                or entry.layer_id in layer_ids
                or entry.position_id in position_ids
            ):
                raise DuplicateValuationEntryError(
                    "Записи стоимости, Ledger, слои и исходные позиции не должны повторяться."
                )
            entry_ids.add(entry.id)
            ledger_ids.add(entry.ledger_entry_id)
            layer_ids.add(entry.layer_id)
            position_ids.add(entry.position_id)
