from dataclasses import dataclass
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError
from src.modules.feed_builder.domain.validation import require_integer


@dataclass(frozen=True, slots=True)
class GenerationSequenceVO:
    """Хранит положительный порядок запроса сборки внутри фида, не версию схемы."""

    value: int

    def __post_init__(self) -> None:
        """Требует положительное целое число, исключая bool."""
        require_integer(self.value, minimum=1, error=InvalidGenerationValueError)
