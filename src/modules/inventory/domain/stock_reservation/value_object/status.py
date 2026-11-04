from enum import StrEnum


class StockReservationStatus(StrEnum):
    """Разделяет удержание, накопленное погашение, освобождение и явное истечение."""

    PENDING = "PENDING"
    PARTIALLY_RESERVED = "PARTIALLY_RESERVED"
    RESERVED = "RESERVED"
    PARTIALLY_CONSUMED = "PARTIALLY_CONSUMED"
    CONSUMED = "CONSUMED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"

    @property
    def is_terminal(self) -> bool:
        """Запрещает повторные изменения закрытого или завершённого по сроку обязательства."""
        return self in (
            StockReservationStatus.RELEASED,
            StockReservationStatus.EXPIRED,
            StockReservationStatus.CONSUMED,
        )
