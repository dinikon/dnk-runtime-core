from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApplyPublicationImportStepResultDTO:
    """Сообщает, был ли принят результат текущего worker шага."""

    applied: bool
