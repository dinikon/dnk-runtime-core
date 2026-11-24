from dataclasses import dataclass
from typing import Literal

from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO


@dataclass(frozen=True, slots=True)
class DocumentFieldExportVO:
    """Задаёт место и форму коллекции объектов в XML-документе."""

    container: ExportNameVO
    item: ExportNameVO
    parent: Literal["ROOT", "SHOP"] = "ROOT"
    layout: Literal["FLAT", "NESTED"] = "FLAT"
    parent_attribute: ExportNameVO = ExportNameVO("parentId")

    def __post_init__(self) -> None:
        """Проверяет имена и поддержанные способы вывода."""
        if (
            not all(
                isinstance(name, ExportNameVO)
                for name in (self.container, self.item, self.parent_attribute)
            )
            or self.parent not in ("ROOT", "SHOP")
            or self.layout not in ("FLAT", "NESTED")
            or self.parent_attribute.value == "xmlns"
        ):
            raise InvalidFeedValueError("Некорректное размещение коллекции XML.")
