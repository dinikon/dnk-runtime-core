from enum import StrEnum


class StageKind(StrEnum):
    """Неизменяемое назначение стадии в процессе."""

    IN_PROGRESS = "in_progress"
    WON = "won"
    LOST = "lost"
