from dataclasses import dataclass
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError
from src.modules.feed_builder.domain.validation import require_integer


@dataclass(frozen=True, slots=True)
class CalculationEngineVersionVO:
    """Хранит положительную версию семантики вычислителя."""

    value: int

    def __post_init__(self) -> None:
        """Требует положительное целое число, исключая bool."""
        require_integer(self.value, minimum=1, error=InvalidGenerationValueError)
