from enum import StrEnum


class ExportFormat(StrEnum):
    """Перечисляет универсальные форматы выгрузки."""

    CSV = "csv"
    XML = "xml"
