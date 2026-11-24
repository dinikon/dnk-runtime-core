from __future__ import annotations
from dataclasses import dataclass
from typing import Self, TYPE_CHECKING
from src.modules.feed_builder.domain.feed.value_object.category_field_type import (
    CategoryFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.field_id import FieldIdVO
from src.modules.feed_builder.domain.feed.value_object.field_key import FieldKeyVO
from src.modules.feed_builder.domain.feed.value_object.field_label import FieldLabelVO
from src.modules.feed_builder.domain.feed.value_object.field_export_settings import (
    FieldExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.string_field_type import (
    StringFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_field_type import (
    TextFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_field_type import (
    MoneyFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.policy.price_calculation_structure import (
    PriceCalculationStructurePolicy,
)
from src.modules.feed_builder.domain.feed.value_object.boolean_field_type import (
    BooleanFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.integer_field_type import (
    IntegerFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.types import FieldTypeDefinition


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    """Равноправное поле с общими свойствами и одним типизированным описанием типа."""

    id: FieldIdVO
    key: FieldKeyVO
    label: FieldLabelVO
    type_definition: FieldTypeDefinition
    export: FieldExportSettingsVO
    ai_instruction: str | None = None

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
    ) -> Self:
        """Создаёт поле с явной идентичностью и готовым описанием его типа."""
        return cls.restore(
            identifier=identifier,
            key=key,
            label=label,
            type_definition=type_definition,
            export=export,
            ai_instruction=ai_instruction,
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
        if not isinstance(
            type_definition,
            (
                StringFieldTypeVO,
                TextFieldTypeVO,
                MoneyFieldTypeVO,
                IntegerFieldTypeVO,
                BooleanFieldTypeVO,
                CategoryFieldTypeVO,
            ),
        ):
            raise InvalidFieldDefinitionError(
                "Нужно одно поддержанное описание типа поля."
            )
        if isinstance(type_definition, CategoryFieldTypeVO):
            properties = {prop.key.value: prop for prop in type_definition.properties}
            if (
                export.enabled
                and export.document is None
                and export.publication_key is None
            ):
                raise InvalidFieldDefinitionError(
                    "Выберите вывод дерева или ссылки для поля категории."
                )
            if export.required and export.publication_key is None:
                raise InvalidFieldDefinitionError(
                    "Обязательность относится к ссылке в предложении."
                )
            if (
                export.publication_key is not None
                and export.publication_key.value not in properties
            ):
                raise InvalidFieldDefinitionError(
                    "Выберите существующее свойство для ссылки в предложении."
                )
            if (
                export.document is not None
                and export.document.layout == "FLAT"
                and any(
                    node.parent_id is not None or node.inherit_parent
                    for node in type_definition.nodes
                )
                and properties[type_definition.id_key].placement == "NONE"
            ):
                raise InvalidFieldDefinitionError(
                    "Для ссылки на родителя выведите свойство ID в дереве."
                )
            if (
                export.document
                and export.document.layout == "FLAT"
                and any(
                    prop.placement == "ATTRIBUTE"
                    and prop.name == export.document.parent_attribute
                    for prop in type_definition.properties
                )
            ):
                raise InvalidFieldDefinitionError(
                    "Атрибут родителя совпадает с атрибутом свойства категории."
                )
        elif (
            export.document is not None
            or export.publication_key is not None
            or export.required
        ):
            raise InvalidFieldDefinitionError(
                "Вывод коллекции доступен полям категории."
            )
        if ai_instruction is not None and (
            not isinstance(ai_instruction, str)
            or len(ai_instruction) > 10000
            or "\x00" in ai_instruction
        ):
            raise InvalidFieldDefinitionError(
                "AI-метаданные должны быть ограниченным текстом."
            )
        if (
            isinstance(type_definition, MoneyFieldTypeVO)
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
        )
