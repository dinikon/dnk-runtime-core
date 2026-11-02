from enum import StrEnum


class TrackingMode(StrEnum):
    """Определяет необходимость идентификации партии и серийного экземпляра."""

    NONE = "NONE"
    LOT = "LOT"
    SERIAL = "SERIAL"
    LOT_AND_SERIAL = "LOT_AND_SERIAL"
