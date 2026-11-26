from dataclasses import dataclass
from typing import ClassVar

from src.modules.feed_builder.domain.feed.field_node.data import FieldNodeData
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError
from src.modules.feed_builder.domain.feed.expression.value_object.boolean_calculation import (
    BooleanCalculationVO,
)
from src.modules.feed_builder.domain.feed.value_object.constant_value_definition import (
    ConstantValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.manual_value_definition import (
    ManualValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)


@dataclass(frozen=True, slots=True)
class BooleanNodeDataVO(FieldNodeData):
    """Определяет источник, константу или расчёт логического поля."""

    kind: ClassVar[FieldValueType] = FieldValueType.BOOLEAN
    value_definition: (
        SourceValueDefinitionVO
        | ConstantValueDefinitionVO
        | ManualValueDefinitionVO
        | BooleanCalculationVO
    )
    required: bool = False

    def __post_init__(self) -> None:
        """Проверяет совместимость определения и логического типа."""
        if (
            type(self.required) is not bool
            or not isinstance(
                self.value_definition,
                (
                    SourceValueDefinitionVO,
                    ConstantValueDefinitionVO,
                    ManualValueDefinitionVO,
                    BooleanCalculationVO,
                ),
            )
            or (
                isinstance(self.value_definition, ConstantValueDefinitionVO)
                and type(self.value_definition.value) is not bool
            )
        ):
            raise InvalidFieldDefinitionError(
                "Некорректные настройки логического поля."
            )
