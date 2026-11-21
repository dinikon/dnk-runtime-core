from enum import StrEnum


class ValidationPolicy(StrEnum):
    """Задаёт строгое поведение при ошибках публикаций."""

    STRICT = "STRICT"
