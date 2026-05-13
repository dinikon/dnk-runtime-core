import enum


class MessageClassVO(str, enum.Enum):
    """Value object класса сообщения."""

    MARKETING = "MARKETING"
    TRANSACTIONAL = "TRANSACTIONAL"
    SERVICE = "SERVICE"
    OTP = "OTP"
    INFO = "INFO"
