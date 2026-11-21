from enum import StrEnum


class ExpirationMode(StrEnum):
    """Разделяет отсутствие дат, необязательные заметки и обязательный контроль."""

    NONE = "NONE"
    OPTIONAL = "OPTIONAL"
    REQUIRED = "REQUIRED"

    @property
    def controls_expiration(self) -> bool:
        """Включает контроль срока и обязательность даты только для REQUIRED."""
        return self is ExpirationMode.REQUIRED
