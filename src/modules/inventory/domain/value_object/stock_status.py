from enum import StrEnum


class StockStatus(StrEnum):
    """Состояние физического запаса независимо от назначения адреса и срока годности."""

    SELLABLE = "SELLABLE"
    QUARANTINE = "QUARANTINE"
    DAMAGED = "DAMAGED"
    BLOCKED = "BLOCKED"
