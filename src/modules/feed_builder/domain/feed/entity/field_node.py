from __future__ import annotations
from dataclasses import dataclass
from typing import Self, TYPE_CHECKING
from uuid import UUID
from src.modules.feed_builder.domain.feed.field_node.data import FieldNodeData
from src.modules.feed_builder.domain.feed.field_node.category.value_object.data import (
    CategoryNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.field_id import FieldIdVO
from src.modules.feed_builder.domain.feed.value_object.field_key import FieldKeyVO
from src.modules.feed_builder.domain.feed.value_object.field_label import FieldLabelVO
from src.modules.feed_builder.domain.feed.value_object.field_export_settings import (
    FieldExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.field_node.money.value_object.data import (
    MoneyNodeDataVO,
)
from src.modules.feed_builder.domain.feed.expression.structure_policy import (
    PriceCalculationStructurePolicy,
)
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.types import FieldTypeDefinition


@dataclass(frozen=True, slots=True)
class FieldNodeDefinition:
    """Равноправное поле с общими свойствами и одним типизированным описанием типа."""

    id: FieldIdVO
    key: FieldKeyVO
    label: FieldLabelVO
    type_definition: FieldTypeDefinition
    export: FieldExportSettingsVO
    ai_instruction: str | None = None
    category_tree_id: UUID | None = None

    @classmethod
    def create(
        cls,
        *,
        identifier: FieldIdVO,
        key: FieldKeyVO,
        label: FieldLabelVO,
        type_definition: FieldTypeDefinition,
        export: FieldExportSettingsVO,
        ai_instruction: str | None = None,
        category_tree_id: UUID | None = None,
    ) -> Self:
        """Создаёт поле с явной идентичностью и готовым описанием его типа."""
        return cls.restore(
            identifier=identifier,
            key=key,
            label=label,
            type_definition=type_definition,
            export=export,
            ai_instruction=ai_instruction,
            category_tree_id=category_tree_id,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: FieldIdVO,
        key: FieldKeyVO,
        label: FieldLabelVO,
        type_definition: FieldTypeDefinition,
        export: FieldExportSettingsVO,
        ai_instruction: str | None = None,
        category_tree_id: UUID | None = None,
    ) -> Self:
        """Восстанавливает общие свойства и проверяет вложенный расчёт зависимого поля."""
        if (
            not isinstance(identifier, FieldIdVO)
            or not isinstance(key, FieldKeyVO)
            or not isinstance(label, FieldLabelVO)
            or not isinstance(export, FieldExportSettingsVO)
        ):
            raise InvalidFieldDefinitionError(
                "Нужны типизированные общие свойства поля."
            )
        if not isinstance(type_definition, FieldNodeData):
            raise InvalidFieldDefinitionError("Нужны типизированные данные ноды.")
        if category_tree_id is not None and (
            not isinstance(category_tree_id, UUID)
            or not isinstance(type_definition, CategoryNodeDataVO)
        ):
            raise InvalidFieldDefinitionError(
                "Ссылка на дерево доступна нодам категории."
            )
        type_definition.validate_export(export)
        if ai_instruction is not None and (
            not isinstance(ai_instruction, str)
            or len(ai_instruction) > 10000
            or "\x00" in ai_instruction
        ):
            raise InvalidFieldDefinitionError(
                "AI-метаданные должны быть ограниченным текстом."
            )
        if (
            isinstance(type_definition, MoneyNodeDataVO)
            and type_definition.value_definition.calculation is not None
        ):
            PriceCalculationStructurePolicy.ensure_valid(
                type_definition.value_definition.calculation
            )
        return cls(
            id=identifier,
            key=key,
            label=label,
            type_definition=type_definition,
            export=export,
            ai_instruction=ai_instruction,
            category_tree_id=category_tree_id,
        )
