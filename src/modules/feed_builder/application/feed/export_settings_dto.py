from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class CsvExportSettingsDTO:
    """Передаёт параметры единственного CSV-формата."""

    format: ClassVar[str] = "csv"
    delimiter: str = ","
    encoding: str = "utf-8"
    include_header: bool = True


@dataclass(frozen=True, slots=True)
class XmlExportSettingsDTO:
    """Передаёт параметры единственного XML-формата."""

    format: ClassVar[str] = "xml"
    root_name: str = "catalog"
    item_name: str = "product"
    encoding: str = "utf-8"


@dataclass(frozen=True, slots=True)
class FeedExportSettingsDTO:
    """Передаёт конкретные параметры выбранного формата между сценариями."""

    format_settings: CsvExportSettingsDTO | XmlExportSettingsDTO
    product_mode: str = "VARIABLE_TO_SINGLE"
    validation_policy: str = "STRICT"
