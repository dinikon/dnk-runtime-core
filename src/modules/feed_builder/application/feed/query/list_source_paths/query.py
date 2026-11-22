from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListSourcePathsQuery:
    """Запрашивает прямые источники в доверенном контексте Console."""
