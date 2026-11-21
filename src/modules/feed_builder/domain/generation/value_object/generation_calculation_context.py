from dataclasses import dataclass
from datetime import datetime
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError
from src.modules.feed_builder.domain.generation.value_object.fx_rate_snapshot import (
    FxRateSnapshotVO,
)
from src.modules.feed_builder.domain.validation import require_datetime


@dataclass(frozen=True, slots=True)
class GenerationCalculationContextVO:
    """Фиксирует время расчёта и необязательный набор курсов для повторных попыток."""

    as_of: datetime
    fx_rate_snapshot: FxRateSnapshotVO | None = None

    def __post_init__(self) -> None:
        """Допускает отсутствие курсов для расчётов без валютных зависимостей."""
        require_datetime(self.as_of, error=InvalidGenerationValueError)
        if self.fx_rate_snapshot is not None and not isinstance(
            self.fx_rate_snapshot, FxRateSnapshotVO
        ):
            raise InvalidGenerationValueError("Нужен снимок валютных курсов либо None.")
