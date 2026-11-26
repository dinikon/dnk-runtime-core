from typing import ClassVar

from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError
from src.modules.feed_builder.domain.feed.value_object.field_export_settings import (
    FieldExportSettingsVO,
)


class FieldNodeData:
    """Задаёт общие правила конфигурации ноды и её участия в выгрузке."""

    __slots__ = ()
    kind: ClassVar[FieldValueType]

    def validate_export(self, export: FieldExportSettingsVO) -> None:
        """Проверяет параметры обычного поля результата."""
        if (
            export.document is not None
            or export.publication_key is not None
            or export.required
        ):
            raise InvalidFieldDefinitionError(
                "Вывод коллекции доступен полям категории."
            )

    def has_publication_output(self, export: FieldExportSettingsVO) -> bool:
        """Определяет участие имени поля в пространстве имён Offer."""
        return True
