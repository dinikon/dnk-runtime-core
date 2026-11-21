from enum import StrEnum


class LocationType(StrEnum):
    """Назначение локации без автоматического изменения состояния запасов."""

    STORAGE = "STORAGE"
    RECEIVING = "RECEIVING"
    SHIPPING = "SHIPPING"
    QUARANTINE = "QUARANTINE"
    TRANSIT = "TRANSIT"
