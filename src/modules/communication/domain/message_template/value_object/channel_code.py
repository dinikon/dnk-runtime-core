import enum


class ChannelCodeVO(str, enum.Enum):
    """Value object кода канала сообщения."""

    SMS = "SMS"
    VIBER = "VIBER"
    EMAIL = "EMAIL"
    CUSTOM = "CUSTOM"
