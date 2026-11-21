from dataclasses import dataclass
from datetime import datetime
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError
from src.modules.feed_builder.domain.generation.value_object.fx_rate import FxRateVO
from src.modules.feed_builder.domain.generation.value_object.fx_rate_snapshot_id import (
    FxRateSnapshotIdVO,
)
from src.modules.feed_builder.domain.validation import require_datetime


@dataclass(frozen=True, slots=True)
class FxRateSnapshotVO:
    """Копирует использованный набор курсов вместе с происхождением и временем."""

    source_snapshot_id: FxRateSnapshotIdVO
    captured_at: datetime
    rates: tuple[FxRateVO, ...]

    def __post_init__(self) -> None:
        """Замораживает набор и запрещает повтор направленной валютной пары."""
        if not isinstance(
            self.source_snapshot_id, FxRateSnapshotIdVO
        ) or not isinstance(self.rates, (list, tuple)):
            raise InvalidGenerationValueError(
                "Нужен типизированный набор валютных курсов."
            )
        require_datetime(self.captured_at, error=InvalidGenerationValueError)
        pairs: set[tuple[CurrencyVO, CurrencyVO]] = set()
        for rate in self.rates:
            if not isinstance(rate, FxRateVO):
                raise InvalidGenerationValueError("Нужен FxRateVO.")
            pair = (rate.source_currency, rate.target_currency)
            if pair in pairs:
                raise InvalidGenerationValueError("Валютная пара повторяется в снимке.")
            pairs.add(pair)
        object.__setattr__(self, "rates", tuple(self.rates))
