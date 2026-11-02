from enum import StrEnum


class ExpirationMode(StrEnum):
    """Задаёт требование к датам будущих партий или серийных экземпляров."""

    DISABLED = "DISABLED"
    REQUIRED = "REQUIRED"
