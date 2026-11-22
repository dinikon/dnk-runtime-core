from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListFieldTypesQuery:
    """Запрашивает типы полей в доверенном контексте Console."""
