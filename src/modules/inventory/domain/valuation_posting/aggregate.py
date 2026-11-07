from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Self

from src.modules.inventory.domain.policy.stock_receipt_valuation_posting import (
    StockReceiptValuationPostingPolicy,
)
from src.modules.inventory.domain.policy.stock_issue_valuation_posting import (
    StockIssueValuationPostingPolicy,
)
from src.modules.inventory.domain.policy.stock_movement_valuation_posting import (
    StockMovementValuationPostingPolicy,
)
from src.modules.inventory.domain.policy.stock_posting_fifo_valuation import (
    StockPostingFifoValuationPolicy,
)
from src.modules.inventory.domain.stock_posting.posting_fifo_plan_snapshot import (
    StockPostingFifoPlanSnapshot,
)
from src.modules.inventory.domain.valuation_layer.consumption_snapshot import (
    ValuationLayerConsumptionSnapshot,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.movement_entry_pair import (
    StockMovementEntryPairVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.valuation_layer.basis_snapshot import (
    ValuationLayerBasisSnapshot,
)
from src.modules.inventory.domain.valuation_layer.movement_consumption_snapshot import (
    ValuationLayerMovementConsumptionSnapshot,
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
from src.modules.inventory.domain.valuation_posting.movement_pair_snapshot import (
    ValuationMovementPairSnapshot,
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
    """Фиксирует неизменяемую стоимость полного физического проведения."""

    id: ValuationPostingIdVO
    stock_posting_id: StockPostingIdVO
    operation_type: StockOperationType
    stock_posted_at: datetime
    posted_at: datetime
    entries: tuple[ValuationEntry, ...]
    movement_pairs: tuple[StockMovementEntryPairVO, ...] = ()

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
    def create_from_issue(
        cls,
        *,
        identifier: ValuationPostingIdVO,
        posting: StockPostingSnapshot,
        consumptions: tuple[ValuationLayerConsumptionSnapshot, ...],
        entry_bindings: tuple[ValuationEntryBindingVO, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        posted_at: datetime,
    ) -> Self:
        """Регистрирует весь ISSUE по заново проверенным результатам без повторного потребления слоёв."""
        entries = StockIssueValuationPostingPolicy.build_entries(
            posting=posting,
            consumptions=consumptions,
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
    def create_from_movement(
        cls,
        *,
        identifier: ValuationPostingIdVO,
        posting: StockPostingSnapshot,
        consumption: ValuationLayerMovementConsumptionSnapshot,
        destination: ValuationLayerBasisSnapshot,
        entry_bindings: tuple[ValuationEntryBindingVO, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        posted_at: datetime,
    ) -> Self:
        """Регистрирует выбытие и поступление стоимости по одной полной паре INTERNAL_MOVE."""
        return cls.create_from_movement_pairs(
            identifier=identifier,
            posting=posting,
            pairs=(ValuationMovementPairSnapshot(consumption, destination),),
            entry_bindings=entry_bindings,
            positions=positions,
            locations=locations,
            posted_at=posted_at,
        )

    @classmethod
    def create_from_movement_pairs(
        cls,
        *,
        identifier: ValuationPostingIdVO,
        posting: StockPostingSnapshot,
        pairs: tuple[ValuationMovementPairSnapshot, ...],
        entry_bindings: tuple[ValuationEntryBindingVO, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        posted_at: datetime,
    ) -> Self:
        """Регистрирует полное INTERNAL_MOVE и сохраняет явные связи записей его пар."""
        entries = StockMovementValuationPostingPolicy.build_entries(
            posting=posting,
            pairs=pairs,
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
            movement_pairs=tuple(pair.consumption.movement.pair for pair in pairs),
        )

    @classmethod
    def create_from_fifo_plan(
        cls,
        *,
        identifier: ValuationPostingIdVO,
        plan: StockPostingFifoPlanSnapshot,
        posting: StockPostingSnapshot,
        consumptions: tuple[ValuationLayerConsumptionSnapshot, ...],
        entry_bindings: tuple[ValuationEntryBindingVO, ...],
        positions: tuple[StockPositionSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        posted_at: datetime,
    ) -> Self:
        """Повторно проверяет полный FIFO-план и регистрирует только его точные результаты без нового потребления."""
        StockPostingFifoValuationPolicy.ensure_consumptions(
            plan=plan, posting=posting, consumptions=consumptions
        )
        return cls.create_from_issue(
            identifier=identifier,
            posting=posting,
            consumptions=consumptions,
            entry_bindings=entry_bindings,
            positions=positions,
            locations=locations,
            posted_at=posted_at,
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
        movement_pairs: tuple[StockMovementEntryPairVO, ...] | None = None,
    ) -> Self:
        """Восстанавливает весь собственный исторический состав без повторной загрузки внешних оснований."""
        posting = cls(
            identifier,
            stock_posting_id,
            operation_type,
            normalize_valuation_posting_time(stock_posted_at),
            normalize_valuation_posting_time(posted_at),
            entries,
            () if movement_pairs is None else movement_pairs,
        )
        posting._validate_structure()
        if operation_type is StockOperationType.INTERNAL_MOVE:
            if movement_pairs is None and len(entries) == 2:
                outgoing, incoming = entries
                if outgoing.quantity_delta.value > 0:
                    outgoing, incoming = incoming, outgoing
                posting = replace(
                    posting,
                    movement_pairs=(
                        StockMovementEntryPairVO(
                            outgoing.ledger_entry_id, incoming.ledger_entry_id
                        ),
                    ),
                )
            posting._ensure_movement_balanced()
        return posting

    def _validate_structure(self) -> None:
        """Проверяет собственные типы, непустой состав, уникальность ссылок и UTC-хронологию факта."""
        if (
            not isinstance(self.id, ValuationPostingIdVO)
            or not isinstance(self.stock_posting_id, StockPostingIdVO)
            or (
                self.operation_type is not StockOperationType.RECEIPT
                and self.operation_type is not StockOperationType.ISSUE
                and self.operation_type is not StockOperationType.INTERNAL_MOVE
            )
            or not isinstance(self.entries, tuple)
            or not self.entries
            or not isinstance(self.movement_pairs, tuple)
            or (
                self.operation_type is not StockOperationType.INTERNAL_MOVE
                and self.movement_pairs
            )
        ):
            raise InvalidValuationPostingValueError(
                "Нужны номинальные ID, допустимая операция, записи стоимости и связи пар только для INTERNAL_MOVE."
            )
        normalize_valuation_posting_time(self.stock_posted_at)
        normalize_valuation_posting_time(self.posted_at)
        if (
            self.stock_posted_at.utcoffset() != timedelta(0)
            or self.posted_at.utcoffset() != timedelta(0)
            or self.posted_at < self.stock_posted_at
        ):
            raise ValuationPostingTimeError(
                "Даты хранятся в UTC; регистрация стоимости не раньше физического проведения."
            )
        entry_ids = set()
        ledger_contexts = {}
        layer_ids = set()
        position_ledgers = {}
        for entry in self.entries:
            if not isinstance(entry, ValuationEntry):
                raise InvalidValuationPostingValueError(
                    "Проведение содержит только дочерние ValuationEntry."
                )
            entry.ensure_valid()
            if (
                self.operation_type is StockOperationType.RECEIPT
                and entry.quantity_delta.value < 0
            ) or (
                self.operation_type is StockOperationType.ISSUE
                and entry.quantity_delta.value > 0
            ):
                raise InvalidValuationPostingValueError(
                    "Направление записи стоимости должно соответствовать виду проведения."
                )
            if entry.id in entry_ids or entry.layer_id in layer_ids:
                raise DuplicateValuationEntryError(
                    "ID записей стоимости и слои не должны повторяться."
                )
            context = (
                entry.position_id,
                entry.inventory_item_id,
                entry.owner_id,
                entry.warehouse_id,
                entry.base_uom,
            )
            if (
                (
                    self.operation_type is not StockOperationType.ISSUE
                    and (
                        entry.ledger_entry_id in ledger_contexts
                        or entry.position_id in position_ledgers
                    )
                )
                or (
                    entry.ledger_entry_id in ledger_contexts
                    and ledger_contexts[entry.ledger_entry_id] != context
                )
                or (
                    entry.position_id in position_ledgers
                    and position_ledgers[entry.position_id] != entry.ledger_entry_id
                )
            ):
                raise DuplicateValuationEntryError(
                    "Ссылки Ledger и позиции уникальны вне расходных групп одного контекста."
                )
            entry_ids.add(entry.id)
            ledger_contexts[entry.ledger_entry_id] = context
            layer_ids.add(entry.layer_id)
            position_ledgers[entry.position_id] = entry.ledger_entry_id

    def _ensure_movement_balanced(self) -> None:
        """Проверяет единый склад, полное покрытие связями и баланс каждой сохранённой пары."""
        if len({entry.warehouse_id for entry in self.entries}) != 1:
            raise InvalidValuationPostingValueError(
                "Все пары стоимости INTERNAL_MOVE должны относиться к одному складу."
            )
        entries = {entry.ledger_entry_id: entry for entry in self.entries}
        covered = set()
        for pair in self.movement_pairs:
            if not isinstance(pair, StockMovementEntryPairVO):
                raise InvalidValuationPostingValueError(
                    "Связи INTERNAL_MOVE должны быть номинальными парами записей Ledger."
                )
            pair.ensure_valid()
            outgoing = entries.get(pair.outgoing_entry_id)
            incoming = entries.get(pair.incoming_entry_id)
            if outgoing is None or incoming is None:
                raise InvalidValuationPostingValueError(
                    "Пара INTERNAL_MOVE ссылается на отсутствующую запись Ledger."
                )
            if pair.outgoing_entry_id in covered or pair.incoming_entry_id in covered:
                raise DuplicateValuationEntryError(
                    "Запись Ledger не должна повторяться в парах стоимости."
                )
            self._ensure_movement_pair_balanced(outgoing, incoming)
            covered.update((pair.outgoing_entry_id, pair.incoming_entry_id))
        if covered != set(entries):
            raise InvalidValuationPostingValueError(
                "Связи INTERNAL_MOVE должны покрывать все записи стоимости."
            )

    @staticmethod
    def _ensure_movement_pair_balanced(
        outgoing: ValuationEntry, incoming: ValuationEntry
    ) -> None:
        """Требует точного погашения количества и стоимости в контексте одной пары."""
        if outgoing.quantity_delta.value >= 0 or (
            outgoing.inventory_item_id,
            outgoing.owner_id,
            outgoing.base_uom,
            outgoing.cost_delta.currency,
            outgoing.quantity_delta.value.copy_negate(),
            outgoing.cost_delta.amount.copy_negate(),
        ) != (
            incoming.inventory_item_id,
            incoming.owner_id,
            incoming.base_uom,
            incoming.cost_delta.currency,
            incoming.quantity_delta.value,
            incoming.cost_delta.amount,
        ):
            raise InvalidValuationPostingValueError(
                "Дельты INTERNAL_MOVE должны точно погашаться для одного товара, владельца, склада, единицы и валюты."
            )
