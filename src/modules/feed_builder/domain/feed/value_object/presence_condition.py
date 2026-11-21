from dataclasses import dataclass
from typing import ClassVar
from src.modules.feed_builder.domain.feed.enum.presence_operator import PresenceOperator
from src.modules.feed_builder.domain.feed.value_object.parameter_reference import (
    ParameterReferenceVO,
)
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class PresenceConditionVO:
    """Описывает явную проверку наличия параметра без обращения к источнику."""

    kind: ClassVar[str] = "presence"
    operator: PresenceOperator
    parameter: ParameterReferenceVO

    def __post_init__(self) -> None:
        """Требует строгие типы операции и ссылки на параметр."""
        if not isinstance(self.operator, PresenceOperator) or not isinstance(
            self.parameter, ParameterReferenceVO
        ):
            raise InvalidFeedValueError(
                "Нужны операция наличия и ParameterReferenceVO."
            )
