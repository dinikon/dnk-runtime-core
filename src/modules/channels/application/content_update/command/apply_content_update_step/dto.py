from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApplyContentUpdateStepResultDTO:
    """Сообщает worker, применён ли факт, включая защиту от старого sequence."""

    applied: bool
