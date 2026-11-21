from dataclasses import dataclass
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError
from src.modules.feed_builder.domain.validation import require_integer


@dataclass(frozen=True, slots=True)
class GenerationCountsVO:
    """Хранит выбранное, выгруженное и отклонённое количество позиций."""

    total_items: int = 0
    exported_items: int = 0
    rejected_items: int = 0

    def __post_init__(self) -> None:
        """Запрещает отрицательные счётчики и превышение общего количества."""
        for value in (self.total_items, self.exported_items, self.rejected_items):
            require_integer(value, minimum=0, error=InvalidGenerationValueError)
        if self.exported_items + self.rejected_items > self.total_items:
            raise InvalidGenerationValueError("Учтённых позиций больше выбранных.")
