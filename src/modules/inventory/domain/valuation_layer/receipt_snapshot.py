from dataclasses import dataclass, field

from src.modules.inventory.domain.valuation_layer.basis_snapshot import (
    ValuationLayerBasisSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerBasisSnapshotError,
    InvalidValuationLayerReceiptSnapshotError,
)


@dataclass(frozen=True, slots=True)
class ValuationLayerReceiptSnapshot(ValuationLayerBasisSnapshot):
    """Передаёт первоначальную стоимость слоя, образованного закупочным приходом."""

    transfer_origin: None = field(default=None, init=False)

    def ensure_valid(self) -> None:
        """Проверяет первоначальные поля и исключает происхождение из переноса."""
        if self.transfer_origin is not None:
            raise InvalidValuationLayerReceiptSnapshotError(
                "Для приходной оценки нужен слой закупочного прихода."
            )
        try:
            ValuationLayerBasisSnapshot.ensure_valid(self)
        except InvalidValuationLayerBasisSnapshotError as exc:
            raise InvalidValuationLayerReceiptSnapshotError(str(exc)) from exc
