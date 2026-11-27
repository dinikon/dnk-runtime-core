from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.feed.enum.xml_field_placement import (
    XmlFieldPlacement,
)
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError
from src.modules.feed_builder.domain.feed.field_node.long_text.value_object.data import (
    LongTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.field_export_settings import (
    FieldExportSettingsVO,
)


class RichTextNodeDataVO(LongTextNodeDataVO):
    """Хранит настройки локализованного HTML с ограничениями видимого текста."""

    __slots__ = ()
    kind = FieldValueType.RICH_TEXT

    def validate_export(self, export: FieldExportSettingsVO) -> None:
        """Разрешает вывод HTML в XML-элемент и обычную ячейку CSV."""
        super().validate_export(export)
        if export.xml_placement is XmlFieldPlacement.ATTRIBUTE:
            raise InvalidFieldDefinitionError(
                "Длинный текст (HTML) выводится в XML-элемент.",
                path=("export", "xml_placement"),
            )
