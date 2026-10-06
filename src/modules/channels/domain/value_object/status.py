from enum import StrEnum


class ChannelStatus(StrEnum):
    """Результат технической проверки, независимый от активности."""

    UNVERIFIED = "unverified"
    CONNECTED = "connected"
    ERROR = "error"
