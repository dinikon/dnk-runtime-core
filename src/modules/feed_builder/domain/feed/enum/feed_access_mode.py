from enum import StrEnum


class FeedAccessMode(StrEnum):
    """Определяет требования к скачиванию активного файла."""

    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
