from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListSystemLocalesQuery:
    """Запрос всех доступных в системе локалей."""
