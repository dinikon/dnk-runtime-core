from dataclasses import dataclass

from src.modules.inventory.domain.valuation_layer.basis_snapshot import (
    ValuationLayerBasisSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import ValuationLayerTimeError
from src.modules.inventory.domain.valuation_layer.movement_consumption_snapshot import (
    ValuationLayerMovementConsumptionSnapshot,
)
from src.modules.inventory.domain.valuation_posting.error import (
    ValuationPostingSourceError,
    ValuationPostingTimeError,
)


@dataclass(frozen=True, slots=True)
class ValuationMovementPairSnapshot:
    """Связывает потребление исходного слоя и первоначальную оценку слоя назначения одной пары."""

    consumption: ValuationLayerMovementConsumptionSnapshot
    destination: ValuationLayerBasisSnapshot

    def ensure_valid(self) -> None:
        """Проверяет переход стоимости, происхождение назначения и порядок регистрации слоёв."""
        if not isinstance(
            self.consumption, ValuationLayerMovementConsumptionSnapshot
        ) or not isinstance(self.destination, ValuationLayerBasisSnapshot):
            raise ValuationPostingSourceError(
                "Нужны снимки потребления и слоя назначения пары."
            )
        destination = self.destination
        destination.ensure_valid()
        if destination.transfer_origin is None:
            raise ValuationPostingSourceError(
                "Для поступления стоимости нужен слой, образованный переносом."
            )
        try:
            expected = self.consumption.destination_basis(
                identifier=destination.id, created_at=destination.created_at
            )
        except ValuationLayerTimeError as exc:
            raise ValuationPostingTimeError(
                "Нужна согласованная хронология потребления и создания слоя назначения."
            ) from exc
        if destination != expected:
            raise ValuationPostingSourceError(
                "Исходная оценка и происхождение слоя назначения должны соответствовать переносу."
            )
