from dataclasses import dataclass
from typing import ClassVar

from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError
from src.modules.feed_builder.domain.feed.value_object.constant_value_definition import (
    MAX_SAFE_INTEGER,
    ConstantValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.manual_value_definition import (
    ManualValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)


@dataclass(frozen=True, slots=True)
class IntegerFieldTypeVO:
    """Определяет источник, константу и ограничения целого поля."""

    kind: ClassVar[FieldValueType] = FieldValueType.INTEGER
    value_definition: (
        SourceValueDefinitionVO | ConstantValueDefinitionVO | ManualValueDefinitionVO
    )
    required: bool = False
    min_value: int | None = None
    max_value: int | None = None

    def __post_init__(self) -> None:
        """Проверяет целочисленные границы и значение константы."""
        if type(self.required) is not bool or not isinstance(
            self.value_definition,
            (
                SourceValueDefinitionVO,
                ConstantValueDefinitionVO,
                ManualValueDefinitionVO,
            ),
        ):
            raise InvalidFieldDefinitionError("Некорректные настройки целого поля.")
        for value in (self.min_value, self.max_value):
            if value is not None and (
                type(value) is not int or abs(value) > MAX_SAFE_INTEGER
            ):
                raise InvalidFieldDefinitionError(
                    "Границы должны быть допустимыми целыми числами."
                )
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise InvalidFieldDefinitionError(
                "Минимум должен быть не больше максимума."
            )
        if isinstance(
            self.value_definition, ConstantValueDefinitionVO
        ) and not self.accepts(self.value_definition.value):
            raise InvalidFieldDefinitionError(
                "Константа должна быть целым числом в границах поля."
            )

    def accepts(self, value: object) -> bool:
        """Проверяет точный тип и допустимый диапазон значения."""
        return (
            type(value) is int
            and abs(value) <= MAX_SAFE_INTEGER
            and (self.min_value is None or value >= self.min_value)
            and (self.max_value is None or value <= self.max_value)
        )
