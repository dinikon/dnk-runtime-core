from enum import StrEnum


class Availability(StrEnum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"


def normalize_availability(value: object, quantity: int | None = None) -> str:
    if quantity is not None:
        return (
            Availability.IN_STOCK.value
            if quantity > 0
            else Availability.OUT_OF_STOCK.value
        )
    normalized = str(value or "").strip().casefold()
    if normalized in {
        "1",
        "true",
        "yes",
        "y",
        "in_stock",
        "в наличии",
        "є в наявності",
        "наявний",
        "available",
    }:
        return Availability.IN_STOCK.value
    if normalized in {
        "0",
        "false",
        "no",
        "n",
        "out_of_stock",
        "нет в наличии",
        "немає в наявності",
        "відсутній",
        "unavailable",
    }:
        return Availability.OUT_OF_STOCK.value
    return Availability.UNKNOWN.value


__all__ = ["Availability", "normalize_availability"]
