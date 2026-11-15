from dataclasses import dataclass
from uuid import UUID
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionValueError,
)


@dataclass(frozen=True, slots=True)
class ReceiptCostAllocationVO:
    """Связывает часть исходной суммы с собственной фактической строкой."""

    execution_line_id: StockExecutionLineIdVO
    amount: MoneyVO

    def __post_init__(self) -> None:
        """Проверяет собственную идентичность, валюту и неотрицательную сумму."""
        if (
            not isinstance(self.execution_line_id, StockExecutionLineIdVO)
            or not isinstance(self.amount, MoneyVO)
            or self.amount.amount < 0
        ):
            raise InvalidStockExecutionValueError(
                "Нужны строка исполнения и неотрицательная сумма распределения."
            )


@dataclass(frozen=True, slots=True)
class ReceiptCostEvidence:
    """Неизменяемое исходное коммерческое основание, а не вычисленная себестоимость."""

    id: UUID
    total: MoneyVO
    basis_kind: str
    source_system: str | None
    source_reference: str | None
    allocations: tuple[ReceiptCostAllocationVO, ...]

    @classmethod
    def create(
        cls,
        *,
        identifier: UUID,
        total: MoneyVO,
        basis_kind: str,
        source_system: str | None,
        source_reference: str | None,
        allocations: tuple[ReceiptCostAllocationVO, ...],
    ) -> "ReceiptCostEvidence":
        """Фиксирует введённую сумму, включая явный ноль, без автоматического распределения."""
        evidence = cls(
            identifier, total, basis_kind, source_system, source_reference, allocations
        )
        evidence.ensure_valid()
        return evidence

    @classmethod
    def restore(
        cls,
        *,
        identifier: UUID,
        total: MoneyVO,
        basis_kind: str,
        source_system: str | None,
        source_reference: str | None,
        allocations: tuple[ReceiptCostAllocationVO, ...],
    ) -> "ReceiptCostEvidence":
        """Восстанавливает первоначальное основание без текущих цен и пересчётов."""
        return cls.create(
            identifier=identifier,
            total=total,
            basis_kind=basis_kind,
            source_system=source_system,
            source_reference=source_reference,
            allocations=allocations,
        )

    def ensure_valid(self) -> None:
        """Проверяет полное либо отсутствующее распределение суммы одной валюты."""
        if (
            not isinstance(self.id, UUID)
            or not isinstance(self.total, MoneyVO)
            or self.total.amount < 0
            or self.basis_kind not in ("MANUAL", "EXTERNAL")
            or not isinstance(self.allocations, tuple)
        ):
            raise InvalidStockExecutionValueError(
                "Некорректное исходное стоимостное основание."
            )
        if self.basis_kind == "EXTERNAL" and (
            not self.source_system or not self.source_reference
        ):
            raise InvalidStockExecutionValueError(
                "Внешнее основание требует источник и ссылку."
            )
        for value in (self.source_system, self.source_reference):
            if value is not None and (
                not isinstance(value, str)
                or not value.strip()
                or len(value) > 200
                or any(ord(c) < 32 for c in value)
            ):
                raise InvalidStockExecutionValueError(
                    "Некорректная ссылка стоимостного основания."
                )
        seen = set()
        total = MoneyVO(self.total.amount * 0, self.total.currency)
        for allocation in self.allocations:
            if (
                not isinstance(allocation, ReceiptCostAllocationVO)
                or allocation.execution_line_id in seen
            ):
                raise InvalidStockExecutionValueError(
                    "Строка распределения передаётся один раз."
                )
            seen.add(allocation.execution_line_id)
            total = total + allocation.amount
        if self.allocations and total != self.total:
            raise InvalidStockExecutionValueError(
                "Распределение должно точно совпадать с суммой основания и валютой."
            )
