from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApplyContentReconciliationResultDTO:
    """Сообщает, принята ли сверка текущего поколения и lease."""

    applied: bool
