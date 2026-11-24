from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.value_object.document_field_export import (
    DocumentFieldExportVO,
)
from src.modules.feed_builder.domain.feed.enum.xml_field_placement import (
    XmlFieldPlacement,
)
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class FieldExportSettingsVO:
    """Определяет участие поля в экспорте и безопасное имя результата."""

    name: ExportNameVO
    enabled: bool = True
    xml_placement: XmlFieldPlacement = XmlFieldPlacement.ELEMENT

    document: DocumentFieldExportVO | None = None
    publication_key: ExportNameVO | None = None
    required: bool = False

    def __post_init__(self) -> None:
        """Проверяет тип имени и явный boolean без неявного приведения."""
        if not isinstance(self.name, ExportNameVO) or type(self.enabled) is not bool:
            raise InvalidFeedValueError("Нужны ExportNameVO и bool участия в экспорте.")
        if (
            self.document is not None
            and not isinstance(self.document, DocumentFieldExportVO)
            or self.publication_key is not None
            and not isinstance(self.publication_key, ExportNameVO)
            or type(self.required) is not bool
        ):
            raise InvalidFeedValueError("Некорректные параметры вывода поля.")
        if not isinstance(self.xml_placement, XmlFieldPlacement):
            raise InvalidFeedValueError(
                "Выберите способ размещения XML-поля.",
                path=("export", "xml_placement"),
            )
        if (
            self.xml_placement is XmlFieldPlacement.ATTRIBUTE
            and self.name.value == "xmlns"
        ):
            raise InvalidFeedValueError(
                "Имя xmlns зарезервировано для пространства имён XML.",
                path=("export", "name"),
            )
