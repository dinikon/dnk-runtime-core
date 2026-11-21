from enum import StrEnum


class SourceProvider(StrEnum):
    """Определяет поддержанных поставщиков прямых значений поля Feed."""

    CATALOG = "catalog"
