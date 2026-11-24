from enum import StrEnum


class ValidationPolicy(StrEnum):
    """Определяет, можно ли публиковать файл при ошибках отдельных позиций."""

    STRICT = "STRICT"
    SKIP_INVALID = "SKIP_INVALID"
