from enum import StrEnum


class PriceListStatus(StrEnum):
    """Допустимые состояния жизненного цикла прайса."""

    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    INVALID = "invalid"
    ARCHIVED = "archived"


class SourceFormat(StrEnum):
    """Поддерживаемые форматы источника."""

    XML = "xml"
    YAML = "yaml"
    XLSX = "xlsx"


__all__ = ["PriceListStatus", "SourceFormat"]
