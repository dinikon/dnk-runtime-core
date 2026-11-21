from dataclasses import dataclass, field
from typing import ClassVar
from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class XmlExportSettingsVO:
    """Хранит безопасные имена корня/предложения и кодировку XML."""

    format: ClassVar[ExportFormat] = ExportFormat.XML
    root_name: ExportNameVO = field(default_factory=lambda: ExportNameVO("catalog"))
    item_name: ExportNameVO = field(default_factory=lambda: ExportNameVO("product"))
    encoding: str = "utf-8"

    def __post_init__(self) -> None:
        """Проверяет типы имён и единственную поддержанную кодировку."""
        if (
            not isinstance(self.root_name, ExportNameVO)
            or not isinstance(self.item_name, ExportNameVO)
            or self.encoding != "utf-8"
        ):
            raise InvalidFeedValueError("XML требует ExportNameVO и UTF-8.")
