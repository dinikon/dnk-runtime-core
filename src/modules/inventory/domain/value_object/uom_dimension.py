from enum import StrEnum


class UomDimension(StrEnum):
    """Разделяет количество, массу, объём, длину и площадь."""

    COUNT = "COUNT"
    MASS = "MASS"
    VOLUME = "VOLUME"
    LENGTH = "LENGTH"
    AREA = "AREA"
