from enum import StrEnum


class PriceListStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    INVALID = "invalid"
    ARCHIVED = "archived"


class SourceFormat(StrEnum):
    XML = "xml"
    YAML = "yaml"
    XLSX = "xlsx"


__all__ = ["PriceListStatus", "SourceFormat"]
