from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CheckTimeZoneResultDTO:
    """Публичный результат проверки timezone без Domain/SQL-объектов."""

    code: str
    is_active: bool
