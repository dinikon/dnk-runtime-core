from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListTransformsQuery:
    """Запрашивает преобразования в доверенном контексте Console."""
