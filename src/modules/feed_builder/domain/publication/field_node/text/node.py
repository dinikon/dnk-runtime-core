from src.modules.feed_builder.domain.feed.field_node.long_text.value_object.data import (
    LongTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.enum.locale_fallback_mode import (
    LocaleFallbackMode,
)
from src.modules.feed_builder.domain.feed.field_node.value_validation import (
    apply_text_transforms,
    valid_text_characters,
)
from src.modules.feed_builder.domain.feed.field_node.short_text.value_object.data import (
    ShortTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_constant_value_definition import (
    TextConstantValueDefinitionVO,
)
from src.modules.feed_builder.domain.publication.value_object.field_override import (
    FieldOverrideVO,
)
from src.modules.feed_builder.domain.publication.value_object.publication_catalog_snapshot import (
    PublicationCatalogSnapshotVO,
)
from src.modules.feed_builder.domain.feed.types import TextFieldType
from src.modules.feed_builder.domain.publication.field_node.base import (
    FieldNode,
    invalid_value,
)
from src.modules.feed_builder.domain.publication.field_node.result import ResolvedField


class TextNode(FieldNode[TextFieldType]):
    """Разрешает текстовые поля и учитывает локали, ограничения и преобразования."""

    data_type = (ShortTextNodeDataVO, LongTextNodeDataVO)

    def check_override(
        self, field: FieldNodeDefinition, override: FieldOverrideVO
    ) -> ResolvedField | None:
        """Проверяет текст, введённый в карточке публикации."""
        settings, value = self.data(field), override.value
        if isinstance(value, str):
            if not valid_text_characters(
                value, multiline=isinstance(settings, LongTextNodeDataVO)
            ):
                return invalid_value(
                    field,
                    "MANUAL",
                    "INVALID_FIELD_VALUE",
                    "Недопустимые символы для этого текстового поля.",
                )
            maximum = settings.constraints.max_length
            if maximum is not None and len(value) > maximum:
                return invalid_value(
                    field,
                    "MANUAL",
                    "TEXT_LENGTH_CONSTRAINT",
                    f"Допустимо не более {maximum} символов.",
                )
        return None

    def resolve_value(
        self,
        field: FieldNodeDefinition,
        settings: TextFieldType,
        snapshot: PublicationCatalogSnapshotVO,
        override: FieldOverrideVO | None,
    ) -> ResolvedField:
        """Выбирает источник значения, затем применяет настройки указанного типа."""
        definition = settings.value_definition
        locale = None
        manual_translation = False
        if override is not None:
            value = override.value
            origin = "MANUAL"
        elif isinstance(definition, TextConstantValueDefinitionVO):
            value = definition.value
            origin = "CONSTANT"
        elif not isinstance(definition, SourceValueDefinitionVO):
            value = None
            origin = "MANUAL"
        elif definition.source.path is CatalogSourcePath.SKU:
            value = snapshot.inputs.sku
            origin = "INHERITED"
        else:
            origin = "INHERITED"
            value = None
            fallback = settings.fallback_policy
            locales = (
                (settings.locale.value, *(code.value for code in fallback.locales))
                if settings.locale is not None and fallback is not None
                else (settings.locale.value,) if settings.locale is not None else ()
            )
            for candidate in locales:
                value = snapshot.text(definition.source.path.value, candidate)
                if value not in (None, ""):
                    locale = candidate
                    break
            manual_translation = (
                value in (None, "")
                and fallback is not None
                and fallback.mode is LocaleFallbackMode.MANUAL_REQUIRED
            )

        if value is not None and not isinstance(value, str):
            return invalid_value(
                field, origin, "INVALID_FIELD_VALUE", "Ожидается текст."
            )
        if value is not None:
            value = apply_text_transforms(value, settings.transforms)
        constraints = settings.constraints
        if manual_translation or (
            constraints.required and (value is None or not value.strip())
        ):
            return invalid_value(
                field, origin, "REQUIRED_VALUE_MISSING", "Требуется значение поля."
            )
        if value is not None and not constraints.accepts_length(value):
            return invalid_value(
                field, origin, "TEXT_LENGTH_CONSTRAINT", "Длина текста вне границ поля."
            )
        return ResolvedField(field.id.uuid, value, origin, locale)
