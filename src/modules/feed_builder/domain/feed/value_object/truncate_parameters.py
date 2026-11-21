from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class TruncateParametersVO:
    """Описывает длину явного обрезания текста без исполнения операции."""

    max_length: int

    def __post_init__(self) -> None:
        """Разрешает неотрицательную целую длину, включая ноль."""
        if type(self.max_length) is not int or self.max_length < 0:
            raise InvalidFeedValueError(
                "Длина truncate должна быть неотрицательным int."
            )
