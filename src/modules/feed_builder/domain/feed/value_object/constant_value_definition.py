from dataclasses import dataclass

from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError

MAX_SAFE_INTEGER = 2**53 - 1


@dataclass(frozen=True, slots=True)
class ConstantValueDefinitionVO:
    """Хранит типизированную константу поля."""

    value: int | bool

    def __post_init__(self) -> None:
        """Проверяет тип и точное представление целого числа в Console."""
        if type(self.value) not in (int, bool) or (
            type(self.value) is int and abs(self.value) > MAX_SAFE_INTEGER
        ):
            raise InvalidFieldDefinitionError(
                "Нужно логическое или допустимое целое значение."
            )
