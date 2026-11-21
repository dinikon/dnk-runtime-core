from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class TextConstraintsVO:
    """Хранит только обязательность и ограничения длины текстового значения."""

    required: bool = False
    min_length: int | None = None
    max_length: int | None = None

    def __post_init__(self) -> None:
        """Проверяет bool, неотрицательные длины и порядок границ."""
        if type(self.required) is not bool:
            raise InvalidFeedValueError("Required должен быть bool.")
        for value in (self.min_length, self.max_length):
            if value is not None and (type(value) is not int or value < 0):
                raise InvalidFeedValueError("Длина должна быть неотрицательным int.")
        if (
            self.min_length is not None
            and self.max_length is not None
            and self.min_length > self.max_length
        ):
            raise InvalidFeedValueError(
                "Минимальная длина не может превышать максимальную."
            )
