from enum import StrEnum


class PresenceOperator(StrEnum):
    """Различает наличие и отсутствие параметра."""

    EXISTS = "EXISTS"
    IS_MISSING = "IS_MISSING"
