from enum import StrEnum


class WarehouseStatus(StrEnum):
    """Состояния склада; создание всегда устанавливает active."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
