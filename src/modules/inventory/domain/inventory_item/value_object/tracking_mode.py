from enum import StrEnum


class TrackingMode(StrEnum):
    """Определяет необходимость идентификации партии и серийного экземпляра."""

    NONE = "NONE"
    LOT = "LOT"
    SERIAL = "SERIAL"
    LOT_AND_SERIAL = "LOT_AND_SERIAL"

    @property
    def requires_serial(self) -> bool:
        """Включает поштучный серийный учёт для SERIAL и LOT_AND_SERIAL."""
        return self in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL)
