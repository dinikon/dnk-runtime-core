from dataclasses import dataclass
from datetime import datetime
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError
from src.modules.feed_builder.domain.validation import require_datetime


@dataclass(frozen=True, slots=True)
class GenerationCalculationContextVO:
    """Фиксирует время расчёта для временных условий и повторных попыток."""

    as_of: datetime

    def __post_init__(self) -> None:
        """Требует явное время без получения курсов и обращения к часам."""
        require_datetime(self.as_of, error=InvalidGenerationValueError)
