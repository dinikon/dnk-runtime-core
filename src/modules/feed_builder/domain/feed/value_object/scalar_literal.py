from dataclasses import dataclass
from typing import ClassVar
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.feed_builder.domain.feed.enum.literal_value_type import (
    LiteralValueType,
)
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class ScalarLiteralVO:
    """Хранит строго типизированную константу UUID, строки или boolean."""

    kind: ClassVar[str] = "scalar"
    value_type: LiteralValueType
    value: EntityIdVO | str | bool

    def __post_init__(self) -> None:
        """Не смешивает boolean, строки UUID и реальные идентификаторы."""
        if not isinstance(self.value_type, LiteralValueType):
            raise InvalidFeedValueError("Нужен тип скалярного литерала.")
        expected = {
            LiteralValueType.UUID: EntityIdVO,
            LiteralValueType.STRING: str,
            LiteralValueType.BOOLEAN: bool,
        }[self.value_type]
        if not isinstance(self.value, expected):
            raise InvalidFeedValueError(
                "Скалярный литерал не соответствует своему типу."
            )
        if isinstance(self.value, str) and (
            len(self.value) > 4096 or "\x00" in self.value
        ):
            raise InvalidFeedValueError(
                "Строковый литерал содержит NUL или слишком длинный."
            )
